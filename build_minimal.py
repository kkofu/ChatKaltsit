#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极简打包脚本
最基础的PyInstaller配置
"""

import os
import sys
import subprocess
from pathlib import Path

print("=== 残瑞赛斯AI助手 - 极简打包 ===\n")

# 检查文件
if not os.path.exists("run_app.py"):
    print("❌ 缺少 run_app.py")
    sys.exit(1)

if not os.path.exists("preset_ai_assistant"):
    print("❌ 缺少 preset_ai_assistant 目录")
    sys.exit(1)

print("✅ 文件检查通过\n")

# 构建最简单的PyInstaller命令
cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--name",
    "PresetAI",
    "--onedir",  # 使用目录模式，更稳定
    "run_app.py",
]

print("开始打包...")
print(f"命令: {' '.join(cmd[:3])} ...\n")

try:
    subprocess.run(cmd, check=True)

    # 检查输出
    dist_dir = Path("dist/PresetAI")
    if dist_dir.exists():
        print("\n✅ 打包成功！")
        print(f"输出目录: {dist_dir.absolute()}")

        # 复制必要文件
        import shutil

        dest_data_dir = dist_dir / "preset_ai_assistant"
        if dest_data_dir.exists():
            shutil.rmtree(dest_data_dir)
        shutil.copytree("preset_ai_assistant", dest_data_dir)

        # 复制.env文件
        shutil.copy(".env", dist_dir / ".env")

        print("✅ 数据文件复制完成")

        # 创建启动脚本
        if sys.platform == "darwin":
            script = dist_dir / "run.sh"
            script.write_text('#!/bin/bash\ncd "$(dirname "$0")"\npython PresetAI\n')
            script.chmod(0o755)
            print(f"✅ 创建启动脚本: {script}")

        print(f"\n🎉 打包完成！")
        print(f"\n运行方法:")
        print(f"  cd {dist_dir}")
        print(f"  ./PresetAI")

    else:
        print("\n❌ 打包失败，未找到输出目录")

except Exception as e:
    print(f"\n❌ 打包失败: {e}")
    import traceback

    traceback.print_exc()
