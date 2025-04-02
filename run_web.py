#!/usr/bin/env python
"""
OpenManus Web界面启动脚本
"""
import asyncio
import argparse
import webbrowser
from app.web_server import run_server

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="运行OpenManus Web界面")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口 (默认: 8000)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print(f"启动OpenManus Web界面于 http://{args.host}:{args.port}")
    print(f"(如果使用默认主机0.0.0.0，可以访问 http://localhost:{args.port})")
    print("\n按Ctrl+C停止服务器\n")

    # 构建访问URL
    url = f"http://localhost:{args.port}" if args.host == "0.0.0.0" else f"http://{args.host}:{args.port}"

    # 启动服务器并打开浏览器
    webbrowser.open(url)
    run_server(host=args.host, port=args.port)
