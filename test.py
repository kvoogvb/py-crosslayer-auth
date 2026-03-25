import unittest
import socket
import rsa
import json
import time

# 服务器配置
HOST = '127.0.0.1'
PORT = 65432

class TestWirelessAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """生成测试所需的密钥对"""
        (cls.pub_a, cls.priv_a) = rsa.newkeys(512)
        (cls.pub_b, cls.priv_b) = rsa.newkeys(512)
        (cls.pub_c, cls.priv_c) = rsa.newkeys(512)

    def _send_request(self, payload):
        """辅助函数：发送请求并获取响应"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps(payload).encode('utf-8'))
            data = s.recv(4096).decode('utf-8')
            return json.loads(data) if data else None

    def test_scenario_1_legal_user(self):
        """测试模块化 handle_registration & handle_authentication: 合法途径"""
        # 1. 注册公钥 (Invoke handle_registration)
        reg_payload = {
            "type": "register",
            "user_id": "Unit_Test_A",
            "public_key": self.pub_a.save_pkcs1().decode('utf-8')
        }
        reg_resp = self._send_request(reg_payload)
        self.assertEqual(reg_resp['status'], 'success')

        # 2. 发起认证 (Invoke handle_authentication)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps({"type": "authenticate", "user_id": "Unit_Test_A"}).encode('utf-8'))
            
            # 接收步骤 2 挑战码
            challenge_data = json.loads(s.recv(4096).decode('utf-8'))
            self.assertEqual(challenge_data['status'], 'challenge')
            challenge_bytes = bytes.fromhex(challenge_data['challenge'])

            # 步骤 3 签名并发送
            signature = rsa.sign(challenge_bytes, self.priv_a, 'SHA-1')
            s.sendall(json.dumps({"signature": signature.hex()}).encode('utf-8'))

            # 步骤 4 检查 [AUTH SUCCESS]
            final_resp = json.loads(s.recv(4096).decode('utf-8'))
            self.assertEqual(final_resp['status'], 'success')

    def test_scenario_2_unregistered_user(self):
        """测试非法接入拦截: 未注册用户"""
        auth_payload = {
            "type": "authenticate",
            "user_id": "Unknown_User"
        }
        resp = self._send_request(auth_payload)
        self.assertEqual(resp['status'], 'fail')
        # 对应 server.py 中的 "User not registered"
        self.assertIn("not registered", resp['message'].lower())

    def test_scenario_3_invalid_signature(self):
        """测试安全防御: 签名不匹配 (冒充攻击)"""
        # 提前注册 Target_User
        self._send_request({
            "type": "register",
            "user_id": "Target_User",
            "public_key": self.pub_a.save_pkcs1().decode('utf-8')
        })

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps({"type": "authenticate", "user_id": "Target_User"}).encode('utf-8'))
            challenge_data = json.loads(s.recv(4096).decode('utf-8'))
            
            # 攻击者用自己的私钥 priv_c 签署 Target_User 的挑战
            challenge_bytes = bytes.fromhex(challenge_data['challenge'])
            wrong_signature = rsa.sign(challenge_bytes, self.priv_c, 'SHA-1')
            s.sendall(json.dumps({"signature": wrong_signature.hex()}).encode('utf-8'))

            final_resp = json.loads(s.recv(4096).decode('utf-8'))
            # 验证 handle_authentication 捕获 VerificationError
            self.assertEqual(final_resp['status'], 'fail')
            self.assertIn("Invalid signature", final_resp['message'])

if __name__ == "__main__":
    unittest.main()
