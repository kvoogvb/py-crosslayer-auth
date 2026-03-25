# 无线网络上下层联动的身份认证实验

## 项目简介 (Project Context)
本实验通过模拟无线网络环境，实现了一个结合**上层密码学认证**与**底层物理层指纹特征**的跨层联动身份认证系统。系统核心利用 RSA 挑战-应答（Challenge-Response）机制，确保接入设备的身份合法性。

## 文件结构 (File Structure)
- [server.py](server.py): **模块化服务端**。
  - `handle_registration`: 注册公钥到内存数据库。
  - `handle_authentication`: 驱动完整的身份认证状态机逻辑。
- [client.py](client.py): **交互式模拟器**。
  - 按照 PPT 逻辑（步骤 1-4）演示合法接入、非法接入、冒充攻击 3 个场景。
- [test.py](test.py): **协议一致性测试**。验证模块化后的函数逻辑与异常处理能力。
- [Wi-Fi data/](Wi-Fi%20data/): 供后续物理层认证扩展使用的发射机指纹 CSV 数据。

## 实验逻辑与流程映射 (Experimental Logic)
本实验的密码学认证部分严格遵循以下四步流程（详见 PPT 流程图）：

1.  **步骤 1: 身份声明 (Identity Claim)**
    - 客户端调用 `client.py` 中的 `authenticate` 发起请求，包含 `user_id`。
    - 服务器 `handle_authentication` 接收并校验 ID 是否已注册。
2.  **步骤 2: 随机数挑战 (Challenge Distribution)**
    - 服务器生成 32 字节安全随机数，并在日志中输出 `[AUTH] 已生成 Challenge`。
3.  **步骤 3: 签名生成 (Response Generation)**
    - 客户端使用本地私钥对挑战码进行 SHA-1 签名。
4.  **步骤 4: 签名验签 (Verification)**
    - 服务器调用 `rsa.verify`。成功则输出 `[AUTH SUCCESS]` 并允许该设备后续进行物理层特征比对。

## 日志标准化说明 (Logging Standard)
为方便 PPT 实验截图，系统采用标准化的日志前缀：
- `[REGISTER]`: 记录公钥注册行为。
- `[AUTH]`: 记录认证过程中的中间状态（步骤 1-3）。
- `[AUTH SUCCESS]`: 明确标识认证通过。
- `[AUTH FAIL]`: 记录被拦截的非法或伪冒尝试。

## 运行指南 (Running Instructions)
1. 启动服务器: `python server.py`
2. 运行客户端演示: `python client.py`
3. 运行自动化验证: `python test.py`

