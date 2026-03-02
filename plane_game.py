#!/usr/bin/env python3
"""启动小飞机弹弓 Web 版（静态页面服务器）"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="小飞机弹弓 Web 可视化版")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="端口，默认 8000")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    web_dir = Path(__file__).resolve().parent / "web"
    if not web_dir.exists():
        raise SystemExit("缺少 web 目录，请确认项目文件完整")

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Web 游戏已启动: http://{args.host}:{args.port}/web/index.html")
        print("按 Ctrl+C 退出")
        if not args.no_browser:
            webbrowser.open(f"http://{args.host}:{args.port}/web/index.html")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
