# 无线网络上下层联动的身份认证实验

## 项目简介 (Project Context)
本实验通过模拟无线网络环境，实现了一个结合**上层密码学认证**与**底层物理层指纹特征**的跨层联动身份认证系统。系统核心利用 RSA 挑战-应答（Challenge-Response）机制，确保接入设备的身份合法性。

## 文件结构 (File Structure)
- [crypto_layer/](crypto_layer/): **上层密码学认证模块**。
  - [server.py](crypto_layer/server.py): 模块化服务端。
    - `handle_registration`: 注册公钥到内存数据库。
    - `handle_authentication`: 驱动完整的身份认证状态机逻辑。
  - [client.py](crypto_layer/client.py): 交互式模拟器。
    - 演示合法接入、未授权接入、签名伪造及**设备克隆攻击**等 4 种跨层实验场景。
- [physical_layer/](physical_layer/): **底层物理层指纹特征认证模块**。
  - `model.py` 等：基于 PyTorch 的一维 ResNet 网络模型进行身份指纹判别。
- [Wi-Fi data/](Wi-Fi%20data/): 供后续物理层认证扩展使用的发射机指纹 CSV 数据。

## 实验逻辑与流程映射 (Experimental Logic)
本实验的密码学认证部分遵循以下四个步骤：

1.  **步骤 1: 身份声明 (Identity Claim)**
    - 客户端调用 `client.py` 中的 `authenticate` 发起请求，包含 `user_id`。
    - 服务器 `handle_authentication` 接收并校验 ID 是否已注册。
2.  **步骤 2: 随机数挑战 (Challenge Distribution)**
    - 服务器生成 32 字节安全随机数，并在日志中输出 `[AUTH] 已生成 Challenge`。
3.  **步骤 3: 签名生成 (Response Generation)**
    - 客户端使用本地私钥对挑战码进行 SHA-1 签名。
4.  **步骤 4: 签名验签与物理层联动 (Cross-layer Verification)**
    - 服务器首先调用 `rsa.verify`，若数字签名合法，则认为应用层身份校验通过。
    - 随即加载实测射频指纹信号并交由 PyTorch 残差网络分析。若真实射频特征与数字身份 (ID) 映射的指纹模型一致，则放行并输出 `[CROSS-LAYER] 跨层双因素身份认证执行完毕`；否则阻断接入。

## 跨层实验演示场景 (Cross-Layer Demonstration Scenarios)
`client.py` 模拟了 4 种系统测试场景及预期结果：

| 场景编号 | 场景描述 | 行为特征 | 拦截层级 | 预期验证结果 |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | **合法接入** (User_A，正确私钥，合法设备) | 使用合法凭证与合法网卡发信。 | **无阻断** | 双因素协同一致验证通过，打印 `[PHYSICAL SUCCESS]` 并允许接入。 |
| **S2** | **未授权接入** (非法身份 User_B) | 使用未注册身份发起认证请求。 | **Layer 1 (密码学层)** | 在查表阶段落入未注册分支，输出 `[AUTH FAIL] User not registered`。 |
| **S3** | **签名伪造** (身份 User_A，错误私钥) | 攻击者使用错误私钥对 Challenge 强行签名。 | **Layer 1 (密码学层)** | 拦截于 RSA 验签阶段，输出 Invalid signature。 |
| **S4** | **设备克隆攻击** (真实私钥，非法发信设备) | 攻击者窃取合法用户的私钥并在异构硬件设备上进行登录，以通过密码学身份验证。 | **Layer 2 (物理层)** | 突破 `server.py` 第一层防线 (`[AUTH SUCCESS]`)；但在物理层被检测到射频特征不符，成功被跨层拦截。 |

## 日志标准化说明 (Logging Standard)
系统采用以下标准化日志前缀：
- `[REGISTER]`: 记录公钥注册行为。
- `[AUTH]`: 记录认证过程中的中间状态（步骤 1-3）。
- `[AUTH SUCCESS]`: 明确标识认证通过。
- `[AUTH FAIL]`: 记录被拦截的非法或伪冒尝试。

## 运行指南 (Running Instructions)

### 方法一：自动化测试脚本
在系统根目录运行集成测试脚本 `run_demo.py`。其将自动在后台挂起服务端并启动客户端进程，按序拉起深度学习计算及验证4种常规与攻击场景。验收完毕后脚本将自动释放系统资源。
```bash
python run_demo.py
```

### 方法二：分步独立运行
开启两个独立终端分别单独运行服务端和客户端：
1. 启动服务器: `cd crypto_layer && python server.py`
2. 启动客户端: `cd crypto_layer && python client.py`

