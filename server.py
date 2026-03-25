import socket
import rsa
import json
import os

# 配置信息
HOST = '127.0.0.1'
PORT = 65432

# 本地公钥数据库: {user_id: rsa.PublicKey}
user_public_keys = {}

def start_server():
    # 创建 TCP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"服务器已启动，监听 {HOST}:{PORT}...")

    while True:
        conn, addr = server_socket.accept()
        try:
            # 接收请求数据
            data = conn.recv(4096).decode('utf-8')
            if not data:
                continue
            
            request = json.loads(data)
            request_type = request.get('type')
            user_id = request.get('user_id')

            if request_type == 'register':
                # 公钥注册请求
                pub_key_pem = request.get('public_key').encode('utf-8')
                pub_key = rsa.PublicKey.load_pkcs1(pub_key_pem)
                user_public_keys[user_id] = pub_key
                print(f"[注册日志] 用户 {user_id} 注册成功。")
                conn.send(json.dumps({"status": "success", "message": "Registration successful"}).encode('utf-8'))

            elif request_type == 'authenticate':
                # 接入认证请求
                print(f"[认证日志] 收到用户 {user_id} 的接入请求。")
                
                if user_id not in user_public_keys:
                    print("密码学认证失败，该设备为非法设备")
                    conn.send(json.dumps({"status": "fail", "message": "User not registered"}).encode('utf-8'))
                else:
                    # 挑战-应答逻辑
                    # 1. 生成随机数挑战
                    challenge = os.urandom(32)
                    # 发送挑战（转换为十六进制字符串传输）
                    conn.send(json.dumps({
                        "status": "challenge", 
                        "challenge": challenge.hex()
                    }).encode('utf-8'))

                    # 2. 接收签名
                    auth_data = conn.recv(4096).decode('utf-8')
                    auth_response = json.loads(auth_data)
                    signature = bytes.fromhex(auth_response.get('signature'))

                    # 3. 验证签名
                    try:
                        # rsa.verify 验证成功不返回或返回 hash 方法名，失败抛出异常
                        rsa.verify(challenge, signature, user_public_keys[user_id])
                        print("密码学认证成功")
                        print("提示：允许进入物理层认证。")
                        conn.send(json.dumps({"status": "success", "message": "Authentication successful"}).encode('utf-8'))
                    except rsa.VerificationError:
                        print("密码学认证失败，该设备为非法设备")
                        conn.send(json.dumps({"status": "fail", "message": "Invalid signature"}).encode('utf-8'))

        except Exception as e:
            print(f"[错误] 处理请求时发生异常: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    start_server()
