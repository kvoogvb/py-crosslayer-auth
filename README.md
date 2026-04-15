# 无线网络上下层联动的身份认证实验

## 项目简介 (Project Context)
本实验通过模拟无线网络环境，实现了一个结合**上层密码学认证**与**底层物理层指纹特征**的跨层联动身份认证系统。系统核心利用 RSA 挑战-应答（Challenge-Response）机制，确保接入设备的身份合法性。

## 文件结构 (File Structure)
- [crypto_layer/](crypto_layer/): **上层密码学认证模块**。
  - [server.py](crypto_layer/server.py): 模块化服务端。
    - `handle_registration`: 注册公钥到内存数据库。
    - `handle_authentication`: 驱动完整的身份认证状态机逻辑。
  - [client.py](crypto_layer/client.py): 交互式模拟器。
    - 按照 PPT 逻辑（步骤 1-4）完整演示合法接入、未授权接入、签名伪造，以及终极的**高级设备克隆攻击**等 4 个跨层验收场景。
- [physical_layer/](physical_layer/): **底层物理层指纹特征认证模块**。
  - `model.py` 等：基于 PyTorch 的一维 ResNet 网络模型进行身份指纹判别。
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
4.  **步骤 4: 签名验签与物理层联动 (Cross-layer Verification)**
    - 服务器首先调用 `rsa.verify`，若数字签名合法，则认为应用层身份校验通过。
    - 随即进入**物理层安全阻断机制**（跨层联动）：加载实测射频指纹信号并交由 PyTorch 残差网络分析。若真实射频特征与数字身份 (ID) 映射的指纹模型高度一致，最终发放 `[CROSS-LAYER] 跨层双因素身份认证执行完毕` 并放行；否则执行强力拦截。

## 跨层实验演示与验收场景 (Cross-Layer Demonstration Scenarios)
为了全面展示本系统的验证逻辑及抗攻击能力，`client.py` 内部模拟了完整的 4 个验收场景及预期理想结果：

| 场景编号 | 场景描述 (Scenario Description) | 攻击手法 / 行为特征 | 理想拦截层级 | 预期验证结果 (Expected Result) |
| :--- | :--- | :--- | :--- | :--- |
| **场景一 (S1)** | **合法主体常规接入验证** (合法身份 User_A，私钥正确，无仿冒发信设备) | 正常使用合法凭证与原始合法网卡设备接入网络。 | **无阻断，全部通过** | 双因素协同一致验证通过，打印 `[PHYSICAL SUCCESS]` 与准予接入信息。 |
| **场景二 (S2)** | **未授权身份强制接入尝试** (非法身份 User_B) | 攻击者未向服务器进行公钥注册登记，贸然发起请求试图撞库或绕过登录。 | **Layer 1 (密码学层)** | 在查表阶段立刻落入未注册分支并被剔除，输出 `[AUTH FAIL] User not registered`。 |
| **场景三 (S3)** | **非授权密钥签名伪造** (身份声明 User_A，错误私钥 priv_c) | 攻击者知道合法用户名，但缺乏对应私钥。使用自己的私钥强行签名后提交服务器。 | **Layer 1 (密码学层)** | 拦截于 RSA 挑战-应答阶段，验签步骤解密数据由于密钥不匹配产生报错，输出 Invalid signature。 |
| **场景四 (S4)**<br>(**联动核心**) | **凭证泄露下的设备克隆攻击** (真实私钥 priv_a 被窃取，攻击者使用自己的非法设备特征 3 发信) | **高阶黑客手段**：攻击者窃取/复制了合法用户的存储密钥并在自己的硬件载体上（如另一块无线网卡）模拟用户活动，从而**完美骗过了第一层密码学验证**。 | **Layer 2 (物理层)** | `server.py` 第一道门防线被攻破（`[AUTH SUCCESS]`）。但随后的多维度特征审计中，**物理层识别模型**瞬间捕获并发现底层射频特征严重不符（声明匹配射频类 1，实测解析属于类 3）。打落报文，触发底层红字告警，成功跨层拦截克隆劫持。 |

## 日志标准化说明 (Logging Standard)
为方便 PPT 实验截图，系统采用标准化的日志前缀：
- `[REGISTER]`: 记录公钥注册行为。
- `[AUTH]`: 记录认证过程中的中间状态（步骤 1-3）。
- `[AUTH SUCCESS]`: 明确标识认证通过。
- `[AUTH FAIL]`: 记录被拦截的非法或伪冒尝试。

## 运行指南 (Running Instructions)
1. 启动服务器: `cd crypto_layer && python server.py`
2. 运行客户端演示: `cd crypto_layer && python client.py`

