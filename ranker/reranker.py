import subprocess
import os
import sys

# ==================== 请根据你的实际目录修改以下三个路径 ====================
# 1. llama-server.exe 的完整路径
LLAMA_SERVER_PATH = r"F:\Services\llama-server.exe"  # 示例，请修改

# 2. 模型文件 (.gguf) 的完整路径
MODEL_PATH = r"F:\Services\models\Qwen3-Reranker-4B-Q4_K_M.gguf"  # 示例，请修改

# 3. 服务监听的端口 (默认8080，可修改)
SERVER_PORT = 8080


# ==========================================================================

def start_server():
    """启动 llama-server 并开启 reranking 端点"""

    # 检查文件是否存在
    if not os.path.exists(LLAMA_SERVER_PATH):
        print(f"❌ 错误: 找不到 llama-server.exe，请检查路径: {LLAMA_SERVER_PATH}")
        return

    if not os.path.exists(MODEL_PATH):
        print(f"❌ 错误: 找不到模型文件，请检查路径: {MODEL_PATH}")
        return

    # 组装启动命令
    cmd = [
        LLAMA_SERVER_PATH,
        "-m", MODEL_PATH,
        "--host", "0.0.0.0",
        "--port", str(SERVER_PORT),
        "--reranking"  # 关键参数，启用 rerank API
    ]

    print("🚀 正在启动 Rerank 服务...")
    print(f"📌 可执行文件: {LLAMA_SERVER_PATH}")
    print(f"📌 模型文件: {MODEL_PATH}")
    print(f"📌 监听地址: http://localhost:{SERVER_PORT}")
    print(f"📌 Rerank 接口: http://localhost:{SERVER_PORT}/rerank")
    print("=" * 50)

    # 启动子进程，输出会实时显示在终端
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 服务已手动停止")
    except Exception as e:
        print(f"❌ 服务运行出错: {e}")


if __name__ == "__main__":
    start_server()