#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版打包脚本
使用最基本的PyInstaller配置
"""

import os
import sys
import subprocess
from pathlib import Path

print("=== 残瑞赛斯AI助手 - 简化打包 ===\n")

# 检查必要文件
required_files = ["run_app.py", "preset_ai_assistant", ".env"]
for file in required_files:
    if not os.path.exists(file):
        print(f"❌ 缺少文件: {file}")
        sys.exit(1)

print("✅ 文件检查通过\n")

# 运行PyInstaller
print("开始打包...")
print("这可能需要几分钟，请耐心等待...\n")

try:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--name",
            "PresetAI",
            "--windowed",
            "--onefile",
            "--add-data",
            "preset_ai_assistant:preset_ai_assistant",
            "--add-data",
            ".env:.",
            "run_app.py",
        ],
        check=True,
    )

    if result.returncode == 0:
        print("\n✅ 打包成功！")
        print(f"\n可执行文件: dist/PresetAI")

        # 创建启动脚本
        if sys.platform == "darwin":  # macOS
            script_content = """#!/bin/bash
cd "$(dirname "$0")"
echo "正在启动普瑞赛斯AI助手..."
./PresetAI
"""
            script_path = Path("dist") / "run_preset_ai.sh"
            script_path.write_text(script_content)
            os.chmod(script_path, 0o755)
            print(f"启动脚本: {script_path}")

        elif sys.platform == "win32":  # Windows
            script_content = """@echo off
cd /d "%~dp0"
echo 正在启动普瑞赛斯AI助手...
PresetAI.exe
"""
            script_path = Path("dist") / "启动助手.bat"
            script_path.write_text(script_content, encoding="gbk")
            print(f"启动脚本: {script_path}")

        print("\n🎉 打包完成！")
        print(f"输出目录: {Path('dist').absolute()}")

    else:
        print("\n❌ 打包失败")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ 打包过程出错: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
