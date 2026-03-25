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
        """场景 1: 合法用户注册并认证成功"""
        # 1. 注册公钥
        reg_payload = {
            "type": "register",
            "user_id": "Test_User_A",
            "public_key": self.pub_a.save_pkcs1().decode('utf-8')
        }
        reg_resp = self._send_request(reg_payload)
        self.assertEqual(reg_resp['status'], 'success')

        # 2. 发起认证
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps({"type": "authenticate", "user_id": "Test_User_A"}).encode('utf-8'))
            
            # 接收挑战
            challenge_data = json.loads(s.recv(4096).decode('utf-8'))
            self.assertIn('challenge', challenge_data)
            challenge_bytes = bytes.fromhex(challenge_data['challenge'])

            # 签名并发送
            signature = rsa.sign(challenge_bytes, self.priv_a, 'SHA-1')
            s.sendall(json.dumps({"signature": signature.hex()}).encode('utf-8'))

            # 检查结果
            final_resp = json.loads(s.recv(4096).decode('utf-8'))
            self.assertEqual(final_resp['status'], 'success')

    def test_scenario_2_unregistered_user(self):
        """场景 2: 未注册用户认证失败"""
        auth_payload = {
            "type": "authenticate",
            "user_id": "Test_User_B"
        }
        resp = self._send_request(auth_payload)
        self.assertEqual(resp['status'], 'fail')
        self.assertIn("not registered", resp['message'].lower())

    def test_scenario_3_attacker_impersonation(self):
        """场景 3: 攻击者冒充他人身份失败"""
        # 注册 User_A 以进行后续模拟
        self._send_request({
            "type": "register",
            "user_id": "Known_User_A",
            "public_key": self.pub_a.save_pkcs1().decode('utf-8')
        })

        # 攻击者使用 Known_User_A 的身份发起请求
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps({"type": "authenticate", "user_id": "Known_User_A"}).encode('utf-8'))
            
            # 接收挑战
            challenge_data = json.loads(s.recv(4096).decode('utf-8'))
            challenge_bytes = bytes.fromhex(challenge_data['challenge'])

            # 攻击者使用自己的私钥 (priv_c) 签名
            signature = rsa.sign(challenge_bytes, self.priv_c, 'SHA-1')
            s.sendall(json.dumps({"signature": signature.hex()}).encode('utf-8'))

            # 检查结果是否失败
            final_resp = json.loads(s.recv(4096).decode('utf-8'))
            self.assertEqual(final_resp['status'], 'fail')

if __name__ == "__main__":
    unittest.main()
