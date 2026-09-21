#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小構成パッケージングスクリプト
最も基本的なPyInstaller設定
"""

import os
import sys
import subprocess
from pathlib import Path

print("=== ChatKaltsit 最小構成パッケージ ===\n")

if not os.path.exists("run_app.py"):
    print("❌ run_app.py がありません")
    sys.exit(1)

if not os.path.exists("data"):
    print("❌ data ディレクトリがありません")
    sys.exit(1)

print("✅ ファイル確認通過\n")

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--name",
    "KaltsitAI",
    "--onedir",
    "run_app.py",
]

print("パッケージング開始...")
print(f"コマンド: {' '.join(cmd[:3])} ...\n")

try:
    subprocess.run(cmd, check=True)

    dist_dir = Path("dist/KaltsitAI")
    if dist_dir.exists():
        print("\n✅ パッケージング成功！")
        print(f"出力ディレクトリ: {dist_dir.absolute()}")

        import shutil

        dest_data_dir = dist_dir / "data"
        if dest_data_dir.exists():
            shutil.rmtree(dest_data_dir)
        shutil.copytree("data", dest_data_dir)

        print("✅ データファイルのコピー完了")

        if sys.platform == "darwin":
            script = dist_dir / "run.sh"
            script.write_text('#!/bin/bash\ncd "$(dirname "$0")"\n./KaltsitAI\n')
            script.chmod(0o755)
            print(f"✅ 起動スクリプトを作成: {script}")

        print(f"\n🎉 パッケージング完了！")
        print(f"\n実行方法:")
        print(f"  cd {dist_dir}")
        print(f"  ./KaltsitAI")

    else:
        print("\n❌ パッケージング失敗。出力ディレクトリが見つかりません")

except Exception as e:
    print(f"\n❌ パッケージング失敗: {e}")
    import traceback

    traceback.print_exc()
