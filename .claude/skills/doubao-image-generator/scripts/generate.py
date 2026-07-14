git#!/usr/bin/env python3
"""
Doubao (豆包) Image Generator - 基于火山引擎 Ark SDK 的 AI 图片生成工具。

依赖安装：
    pip install 'volcengine-python-sdk[ark]'

API Key 配置：
    设置环境变量 DOUBAO_API_KEY，或通过 --api-key 参数传入。
    获取地址：https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement

限流说明：
    API 有频率限制，脚本内置 5 秒间隔，批量生成时自动等待。
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import urlretrieve

# 限流控制：记录上次调用时间，确保间隔 >= 5 秒
_last_call_time = 0.0
_RATE_LIMIT_SECONDS = 5.0


def _rate_limit_wait():
    """限流等待：确保两次 API 调用间隔至少 5 秒。"""
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _RATE_LIMIT_SECONDS:
        wait_time = _RATE_LIMIT_SECONDS - elapsed
        print(f"[限流] 等待 {wait_time:.1f}s ...", file=sys.stderr)
        time.sleep(wait_time)
    _last_call_time = time.time()


def generate_image(
    prompt: str,
    output_path: str,
    api_key: str,
    model: str = "doubao-seedream-5.0-lite",
    size: str = "2K",
    output_format: str = "png",
    watermark: bool = False,
) -> str:
    """
    调用豆包 API 生成图片并保存到本地。

    Args:
        prompt: 图片生成提示词
        output_path: 图片保存路径
        api_key: API Key
        model: 模型名称
        size: 图片尺寸（2K / 1K）
        output_format: 输出格式（png / jpg / webp）
        watermark: 是否添加水印

    Returns:
        保存的图片路径
    """
    from volcenginesdkarkruntime import Ark

    client = Ark(
        base_url="https://ark.cn-beijing.volces.com/api/plan/v3",
        api_key=api_key,
    )

    print(f"[生成] 模型: {model} | 尺寸: {size} | 格式: {output_format}")
    print(f"[Prompt] {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

    _rate_limit_wait()

    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            output_format=output_format,
            response_format="url",
            watermark=watermark,
        )
    except Exception as e:
        print(f"[错误] API 调用失败: {e}", file=sys.stderr)
        sys.exit(1)

    image_url = response.data[0].url
    print(f"[响应] 图片 URL: {image_url}")

    # 下载图片并保存
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # 确保扩展名正确
    if not output.suffix:
        output = output.with_suffix(f".{output_format}")

    print(f"[下载] 保存到: {output}")
    urlretrieve(image_url, str(output))
    print(f"[完成] {output} ({output.stat().st_size:,} bytes)")

    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description="豆包 (Doubao) AI 图片生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 基本用法
  python generate.py --prompt "一只可爱的猫" --output cat.png

  # 指定尺寸和格式
  python generate.py --prompt "赛博朋克城市" --output city.jpg --size 1K --format jpg

  # 从文件读取 prompt（文件内容作为提示词）
  python generate.py --prompt-file prompt.txt --output result.png

API Key 优先级（从高到低）：
  1. --api-key 命令行参数
  2. DOUBAO_API_KEY 环境变量
  3. AGENT_API_KEY 环境变量（兼容旧版命名）
""",
    )
    parser.add_argument("--prompt", "-p", help="图片生成提示词")
    parser.add_argument("--prompt-file", help="从文件读取提示词")
    parser.add_argument("--output", "-o", required=True, help="图片保存路径")
    parser.add_argument(
        "--model",
        default="doubao-seedream-5.0-lite",
        help="模型名称（默认: doubao-seedream-5.0-lite）",
    )
    parser.add_argument(
        "--size", default="2K", choices=["1K", "2K"], help="图片尺寸（默认: 2K）"
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg", "webp"],
        dest="output_format",
        help="输出格式（默认: png）",
    )
    parser.add_argument(
        "--watermark", action="store_true", help="添加水印（默认不添加）"
    )
    parser.add_argument(
        "--api-key",
        help="API Key（优先级高于环境变量）",
    )

    args = parser.parse_args()

    # 获取 prompt
    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if not prompt:
        parser.error("必须提供 --prompt 或 --prompt-file")

    # 获取 API Key（优先级：命令行 > DOUBAO_API_KEY > AGENT_API_KEY）
    api_key = args.api_key or os.getenv("DOUBAO_API_KEY") or os.getenv("AGENT_API_KEY")
    if not api_key:
        print(
            "[错误] 未提供 API Key。请通过以下方式之一设置：\n"
            "  1. 命令行: --api-key <YOUR_KEY>\n"
            "  2. 环境变量: export DOUBAO_API_KEY=<YOUR_KEY>\n"
            "  3. 环境变量: export AGENT_API_KEY=<YOUR_KEY> (兼容旧版)\n\n"
            "获取 API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement",
            file=sys.stderr,
        )
        sys.exit(1)

    generate_image(
        prompt=prompt,
        output_path=args.output,
        api_key=api_key,
        model=args.model,
        size=args.size,
        output_format=args.output_format,
        watermark=args.watermark,
    )


if __name__ == "__main__":
    main()
