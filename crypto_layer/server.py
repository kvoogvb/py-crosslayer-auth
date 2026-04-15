import socket
import rsa
import json
import os
import sys

# 把根目录加到 sys.path 中，以便可以从 physical_layer 导入
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
# 将物理层目录也加入路径，因为其内部 import 相互之间采用的是相对引用的短写
sys.path.append(os.path.join(BASE_DIR, 'physical_layer'))

from physical_layer.val import Val

# 配置信息
HOST = '127.0.0.1'
PORT = 65432

# 物理层全局模型引用
physical_model = None

# 映射：声明的身份 对应的 合法物理射频指纹库ID
user_to_physical_id = {
    "User_A": 1,
    "User_B": 2,
    "User_C": 3
}

# 本地公钥数据库: {user_id: rsa.PublicKey}
user_public_keys = {}

def handle_registration(conn, request):
    """
    处理公钥注册请求
    对应流程图中的: [公私钥 -> (虚线) -> 公钥] 注册过程
    """
    user_id = request.get('user_id')
    pub_key_pem = request.get('public_key').encode('utf-8')
    try:
        pub_key = rsa.PublicKey.load_pkcs1(pub_key_pem)
        user_public_keys[user_id] = pub_key
        print(f"\n[REGISTER] 收到注册请求: {user_id}")
        print(f"[REGISTER] 已成功存储 {user_id} 的 RSA 公钥")
        
        response = {"status": "success", "message": "Registration successful"}
        conn.sendall(json.dumps(response).encode('utf-8'))
    except Exception as e:
        print(f"[REGISTER ERROR] 注册失败: {e}")

def handle_authentication(conn, request):
    """
    处理挑战-应答接入认证
    对应流程图中的: ①发起请求 -> ②挑战码 -> ③解密签名 -> ④验证成功
    """
    user_id = request.get('user_id')
    simulate_wifi_id = request.get('simulate_wifi_id')
    print(f"\n[AUTH] 收到用户 {user_id} 的接入认证请求 (步骤 1)")

    # 1. 验证用户是否存在
    if user_id not in user_public_keys:
        print(f"[AUTH FAIL] 密码学认证失败: 用户 {user_id} 未在系统中注册 (非法设备)")
        conn.sendall(json.dumps({"status": "fail", "message": "User not registered"}).encode('utf-8'))
        return

    # 2. 生成并发送挑战码 (步骤 2)
    challenge = os.urandom(32)
    print(f"[AUTH] 已生成 32 字节 Challenge (随机数): {challenge.hex()}")
    conn.sendall(json.dumps({
        "status": "challenge", 
        "challenge": challenge.hex()
    }).encode('utf-8'))

    # 3. 接收客户端签名并进行验签 (步骤 3 & 4)
    try:
        auth_data = conn.recv(4096).decode('utf-8')
        if not auth_data: return
        
        auth_response = json.loads(auth_data)
        signature = bytes.fromhex(auth_response.get('signature'))
        
        # RSA 验签核心逻辑
        rsa.verify(challenge, signature, user_public_keys[user_id])
        
        print(f"[AUTH SUCCESS] 密码学认证成功！")
        print(f"[HINT] 业务逻辑: 校验通过，允许该设备进入下一阶段：物理层特征分析。")
        
        # ===== 双因子第二层：触发物理层射频特征校验 =====
        if simulate_wifi_id is None or physical_model is None:
            # 兼容老客户端不带物理特征参数
            conn.sendall(json.dumps({"status": "success", "message": "Authentication successful (No physical check)"}).encode('utf-8'))
            return
            
        print(f"[PHYSICAL] ---- 跨层联动触发 ----")
        expected_id = user_to_physical_id.get(user_id, 1) # User_A 期望它是发射特征 1
        print(f"[PHYSICAL] 正在提取底层通信接收到的实测射频指纹信号... (模拟底层传入 ID: {simulate_wifi_id})")
        
        ans, cost = physical_model.val([expected_id], [simulate_wifi_id])
        
        if ans and ans[0] is True:
            print(f"[PHYSICAL SUCCESS] 物理层射频指纹与应用层数字身份声明 ({user_id}) 全局一致性比对通过。推理周期: {cost:.5f} 秒。")
            print(f"[CROSS-LAYER] \033[92m跨层双因素身份认证执行完毕，准予核心网络接入。\033[0m")
            conn.sendall(json.dumps({"status": "success", "message": "Cross-layer MFA verification successful"}).encode('utf-8'))
        else:
            print(f"[PHYSICAL FAIL] 安全审计告警：检测到非匹配射频指纹。应用协议内声明身份 ({expected_id}) 与空口解析实际物理特征 ({simulate_wifi_id}) 存在显著冲突！")
            print(f"[CROSS-LAYER] \033[91m接入拒绝：跨层防御机制成功检出并阻截设备硬件克隆攻击。\033[0m")
            conn.sendall(json.dumps({"status": "fail", "message": "Identity mismatch detected by RF fingerprint analytical model"}).encode('utf-8'))
        
    except rsa.VerificationError:
        print(f"[AUTH FAIL] 密码学认证失败: {user_id} 提交的数字签名无效 (非法/伪造设备)")
        conn.sendall(json.dumps({"status": "fail", "message": "Invalid signature"}).encode('utf-8'))
    except Exception as e:
        print(f"[AUTH ERROR] 流程异常: {e}")

def start_server():
    global physical_model
    
    # 预初始化深度学习计算图与模型参数，规避通信并发引发的过量 IO 装载延迟
    print("[SYSTEM] 正在初始化物理层深度特征提取与分类模型...")
    data_dir = os.path.join('physical_layer', 'data')
    model_dir = os.path.join('physical_layer', 'save', 'v5_ok.pth')
    if os.path.exists(data_dir):
        physical_model = Val(data_dir, model_dir)
        print("[SYSTEM] 物理层网络射频特征检测分类器装载就绪。")
        
    # 创建 TCP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print("==========================================")
    print(f"无线网络跨层认证服务器 (密码学部分) 已启动")
    print(f"监听地址: {HOST}:{PORT}")
    print("==========================================")

    while True:
        conn, addr = server_socket.accept()
        try:
            data = conn.recv(4096).decode('utf-8')
            if not data: continue
            
            request = json.loads(data)
            request_type = request.get('type')

            if request_type == 'register':
                handle_registration(conn, request)
            elif request_type == 'authenticate':
                handle_authentication(conn, request)

        except Exception as e:
            print(f"[SYSTEM ERROR] 请求分发异常: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    start_server()
