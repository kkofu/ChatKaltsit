#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
普瑞赛斯AI对话助手 - 启动入口
打包版本的主入口文件
"""

import os
import sys
import webbrowser
import time
import threading
from pathlib import Path

# 确保导入路径正确
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))


def check_environment():
    """检查运行环境"""
    print("=== 普瑞赛斯AI对话助手 ===")
    print("正在初始化...")

    # 检查数据文件
    data_dir = current_dir / "preset_ai_assistant"
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        print("请确保包含了必要的数据文件")
        return False

    # 检查对话数据
    dialogues_file = data_dir / "preset_dialogues.csv"
    if not dialogues_file.exists():
        print(f"❌ 对话数据文件不存在: {dialogues_file}")
        return False

    print("✅ 环境检查通过")
    return True


def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open("http://localhost:8080")


def main():
    """主函数"""
    if not check_environment():
        input("按回车键退出...")
        sys.exit(1)

    try:
        from preset_ai_assistant import app, init_dialogue_system

        # 初始化对话系统
        init_dialogue_system()

        print("\n" + "=" * 50)
        print("服务器启动成功！")
        print("=" * 50)
        print("\n访问地址:")
        print("  - http://localhost:8080")
        print("  - http://127.0.0.1:8080")
        print("\n按 Ctrl+C 停止服务器")
        print("=" * 50 + "\n")

        # 在后台线程中打开浏览器
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()

        # 启动Flask应用
        app.run(host="0.0.0.0", port=8080, debug=False)

    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback

        traceback.print_exc()
        input("按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
