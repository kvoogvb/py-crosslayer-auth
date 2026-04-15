import socket
import rsa
import json
import os

# 服务器配置
HOST = '127.0.0.1'
PORT = 65432

def generate_keys():
    """生成 RSA 公私钥对 (512位用于实验展示)"""
    print("[SYSTEM] 正在生成 RSA 密钥对...")
    (pub_key, priv_key) = rsa.newkeys(512)
    return pub_key, priv_key

def register(user_id, pub_key):
    """向服务器注册公钥"""
    print(f"\n[REGISTER] 正在为用户 {user_id} 发起公钥注册...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            pub_key_pem = pub_key.save_pkcs1().decode('utf-8')
            payload = {
                "type": "register",
                "user_id": user_id,
                "public_key": pub_key_pem
            }
            s.sendall(json.dumps(payload).encode('utf-8'))
            response = json.loads(s.recv(4096).decode('utf-8'))
            print(f"[REGISTER] 服务器响应: {response.get('message')}")
            return response.get('status') == 'success'
    except Exception as e:
        print(f"[ERROR] 注册失败: {e}")
        return False

def authenticate(user_id, priv_key, simulate_wifi_id=1, label="认证"):
    """执行挑战-应答身份认证流程 (对应步骤 1-4)"""
    print(f"\n[AUTH] === {label}: 用户 {user_id} 发起流程 ===")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            
            # 步骤 1: 发起初步接入请求 (Identity Claim)
            print(f"[AUTH] 步骤 1: 发送身份声明请求 (User ID: {user_id}), 并携带底层模拟特征({simulate_wifi_id})")
            auth_request = {
                "type": "authenticate",
                "user_id": user_id,
                "simulate_wifi_id": simulate_wifi_id
            }
            s.sendall(json.dumps(auth_request).encode('utf-8'))
            
            # 步骤 2: 接收挑战码 (Challenge)
            resp_data = s.recv(4096).decode('utf-8')
            if not resp_data:
                return False
            response = json.loads(resp_data)
            
            if response.get('status') == 'fail':
                print(f"[AUTH FAIL] 步骤 2 失败: {response.get('message')}")
                return False

            challenge_hex = response.get('challenge')
            print(f"[AUTH] 步骤 2: 收到服务器随机数挑战 (Challenge): {challenge_hex}")
            challenge_bytes = bytes.fromhex(challenge_hex)

            # 步骤 3: 客户端使用私钥生成数字签名 (Response Generation)
            print(f"[AUTH] 步骤 3: 客户端使用私钥生成数字签名 (RSA Sign)")
            signature = rsa.sign(challenge_bytes, priv_key, 'SHA-1')
            
            # 发送签名结果
            sig_payload = {
                "signature": signature.hex()
            }
            s.sendall(json.dumps(sig_payload).encode('utf-8'))
            
            # 步骤 4: 接收最终认证结论 (Verification)
            final_resp_data = s.recv(4096).decode('utf-8')
            if not final_resp_data:
                return False
            final_resp = json.loads(final_resp_data)
            
            if final_resp.get('status') == 'success':
                print(f"[AUTH SUCCESS] 步骤 4: {final_resp.get('message')}")
            else:
                print(f"[AUTH FAIL] 步骤 4: {final_resp.get('message')}")
            return final_resp.get('status') == 'success'

    except Exception as e:
        print(f"[AUTH ERROR] 流程异常: {e}")
        return False

if __name__ == "__main__":
    print("====================================================")
    print("   无线网络跨层联动身份认证实验 - 客户端模拟程序   ")
    print("====================================================")

    # 准备密钥对
    pub_a, priv_a = generate_keys() # 用户 A (合法用户, 设备指纹属于 1)
    pub_b, priv_b = generate_keys() # 用户 B (未注册用户, 设备指纹属于 2)
    pub_c, priv_c = generate_keys() # 用户 C (伪装攻击者, 设备指纹属于 3)

    # --- 场景 1: 用户A (合法主体接入) ---
    print("\n--- 场景 1: 合法用户常规接入验证 (跨层双因素认证通过) ---")
    if register("User_A", pub_a):
        authenticate("User_A", priv_a, simulate_wifi_id=1, label="场景 1")

    # --- 场景 2: 用户B (未授权身份接入尝试) ---
    print("\n--- 场景 2: 未授权终端接入尝试 (密码学认证层检测并阻断) ---")
    authenticate("User_B", priv_b, simulate_wifi_id=2, label="场景 2")

    # --- 场景 3: 用户C (非授权密钥签名伪造) ---
    print("\n--- 场景 3: 非法终端使用末匹配密钥进行身份伪造 (密码学签名校验失败) ---")
    register("User_C", pub_c) 
    authenticate("User_A", priv_c, simulate_wifi_id=3, label="场景 3")

    # --- 场景 4: 凭证泄露下的设备克隆攻击 (跨层防范演练) ---
    print("\n--- 场景 4: \033[93m【跨层联动安全演练】\033[0m 应用层密钥泄露环境下的高级设备克隆攻击防御 ---")
    # 威胁模型假设：攻击者已完整窃取合法用户 (User_A) 的数字密钥 (priv_a)，能够成功规避应用层的密码学防线。
    # 防御行为：系统截获实测物理层空口信号，由于入侵者发射端硬件的射频指纹（特征类型：3）与声明身份应匹配的合法特征（特征类型：1）存在本质差异，触发底层强制拦截。
    authenticate("User_A", priv_a, simulate_wifi_id=3, label="场景 4")

    print("\n[SYSTEM] 所有测试场景演练及跨层验证结束。")
