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

def authenticate(user_id, priv_key, label="认证"):
    """执行挑战-应答身份认证流程 (对应步骤 1-4)"""
    print(f"\n[AUTH] === {label}: 用户 {user_id} 发起流程 ===")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            
            # 步骤 1: 发起初步接入请求 (Identity Claim)
            print(f"[AUTH] 步骤 1: 发送身份声明请求 (User ID: {user_id})")
            auth_request = {
                "type": "authenticate",
                "user_id": user_id
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
    pub_a, priv_a = generate_keys() # 用户 A (合法用户)
    pub_b, priv_b = generate_keys() # 用户 B (未注册用户)
    pub_c, priv_c = generate_keys() # 用户 C (伪装攻击者)

    # --- 场景 1: 用户A (合法用户) ---
    print("\n--- 场景 1: 合法用户正常接入流程 ---")
    if register("User_A", pub_a):
        authenticate("User_A", priv_a, label="场景 1")

    # --- 场景 2: 用户B (未注册用户) ---
    print("\n--- 场景 2: 未注册非法用户尝试接入 ---")
    authenticate("User_B", priv_b, label="场景 2")

    # --- 场景 3: 用户C (伪装攻击者) ---
    print("\n--- 场景 3: 攻击者冒用 User_A 身份尝试接入 ---")
    # 哪怕攻击者自己注册过 (User_C)，但冒用 A 的 ID 时签名会失效
    register("User_C", pub_c) 
    authenticate("User_A", priv_c, label="场景 3")

    print("\n[SYSTEM] 所有测试场景演练结束。")
