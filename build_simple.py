#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡易版パッケージングスクリプト
最も基本的なPyInstaller設定を使用
"""

import os
import sys
import subprocess
from pathlib import Path

print("=== ChatKaltsit 簡易パッケージ ===\n")

required_files = ["run_app.py", "data"]
for file in required_files:
    if not os.path.exists(file):
        print(f"❌ ファイルがありません: {file}")
        sys.exit(1)

print("✅ ファイル確認通過\n")

print("パッケージング開始...")
print("数分かかる場合があります。そのままお待ちください...\n")

try:
    sep = ";" if sys.platform == "win32" else ":"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--name",
            "KaltsitAI",
            "--windowed",
            "--onefile",
            "--add-data",
            f"data{sep}data",
            "run_app.py",
        ],
        check=True,
    )

    if result.returncode == 0:
        print("\n✅ パッケージング成功！")
        print(f"\n実行ファイル: dist/KaltsitAI")

        if sys.platform == "darwin":
            script_content = """#!/bin/bash
cd "$(dirname "$0")"
echo "ChatKaltsit を起動しています..."
./KaltsitAI
"""
            script_path = Path("dist") / "run_kaltsit.sh"
            script_path.write_text(script_content)
            os.chmod(script_path, 0o755)
            print(f"起動スクリプト: {script_path}")

        elif sys.platform == "win32":
            script_content = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ChatKaltsit を起動しています...
KaltsitAI.exe
"""
            script_path = Path("dist") / "ケルシー起動.bat"
            script_path.write_text(script_content, encoding="cp932")
            print(f"起動スクリプト: {script_path}")

        print("\n🎉 パッケージング完了！")
        print(f"出力ディレクトリ: {Path('dist').absolute()}")

    else:
        print("\n❌ パッケージング失敗")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ パッケージング中にエラー: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
