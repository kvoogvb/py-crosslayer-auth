import os
import sys
import time
import subprocess

def main():
    print("==================================================")
    print("   无线网络跨层身份认证系统 - 验证脚本")
    print("==================================================\n")

    # 配置 Python 解释器 (优先使用 .venv)
    venv_python = os.path.join(".venv", "Scripts", "python.exe") if os.name == 'nt' else os.path.join(".venv", "bin", "python")
    if not os.path.exists(venv_python):
        print(f"[警告] 未找到虚拟环境 {venv_python}，降级使用系统默认 Python。")
        venv_python = sys.executable

    # 1. 启动服务端进程
    print("[系统] 启动认证服务器 (Server)...")
    server_process = subprocess.Popen(
        [venv_python, os.path.join("crypto_layer", "server.py")]
    )

    # 等待模型加载与服务初始化
    print("[系统] 等待模型加载与服务初始化 (10s)...\n")
    time.sleep(10)

    # 2. 启动客户端并执行场景测试
    print("[系统] 启动客户端发起认证请求 (Client)...\n")
    try:
        subprocess.run(
            [venv_python, os.path.join("crypto_layer", "client.py")],
            check=True
        )
    except KeyboardInterrupt:
        print("\n[中止] 用户终端执行。")
    except Exception as e:
        print(f"\n[错误] 客户端异常: {e}")
    finally:
        # 3. 资源回收
        print("\n[清理] 终止服务器进程...")
        server_process.terminate()
        server_process.wait()
        print("[结束] 验证流程完毕。")

if __name__ == "__main__":
    main()