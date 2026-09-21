#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ミニ版パッケージングスクリプト
- 既存コードは書き換えずビルド時にミニ版 (*_mini.py) を自動生成、ビルド成功後削除
- 除外: matplotlib / pandas / numpy / janome
  - matplotlib: ランタイム到達範囲外 (分析スクリプト用)
  - pandas/numpy: CSV読込1箇所のみ -> 標準csv+最小シムに置換
  - janome: キーワード抽出のみ -> 正規表現フォールバック
- データ同梱はランタイム必須の2ファイルのみ (kaltsit_dialogues.csv / kaltsit_character_profile.json)
"""

import os
import glob
import platform
import subprocess
import sys
from pathlib import Path

APP_NAME = "KaltsitAI-mini"
ENTRY = "run_mini.py"

# ランタイム必須データ (SRC は実ファイル、DEST はコードが読むパス)
DATA_FILES = [
    "data/kaltsit_dialogues.csv",
    "data/kaltsit_character_profile.json",
]
DATA_DEST = "data"

EXCLUDE_MODULES = ["matplotlib", "pandas", "numpy", "janome"]


_MINI_SHIM = '''class _MiniSeries:
    # pandas Series の最小代替 (content列の astype -> tolist のみ対応)

    def __init__(self, values):
        self._values = values

    def astype(self, dtype):
        return self

    def tolist(self):
        return ["" if v is None else str(v) for v in self._values]


class _MiniDF:
    # pandas DataFrame の最小代替 (列参照のみ対応)

    def __init__(self, rows):
        self._rows = rows

    def __getitem__(self, col):
        return _MiniSeries([r.get(col, "") for r in self._rows])
'''

_LOAD_DIALOGUES_OLD = '''    def _load_dialogues(self, file_path: str) -> Any:
        import pandas as pd

        return pd.read_csv(file_path)
'''

_LOAD_DIALOGUES_NEW = '''    def _load_dialogues(self, file_path: str) -> Any:
        # 対話データ読み込み (ミニ版: 標準csvのみ。BOM付き対応)
        import csv

        with open(file_path, encoding="utf-8-sig", newline="") as f:
            return _MiniDF(list(csv.DictReader(f)))
'''


def _replace_once(text: str, old: str, new: str, where: str) -> str:
    n = text.count(old)
    if n != 1:
        print(f"❌ 置換アンカー異常 ({where}): {n}件ヒット")
        sys.exit(1)
    return text.replace(old, new)


def generate_mini_modules():
    print("=== ミニ版を生成 ===\n")

    core = Path("core.py").read_text(encoding="utf-8")
    core = _replace_once(
        core,
        _LOAD_DIALOGUES_OLD,
        _LOAD_DIALOGUES_NEW,
        "core._load_dialogues",
    )
    # シムはモジュール末尾に追記 (クラス本体の途中割込を避けるため)
    core = core.rstrip("\n") + "\n\n\n" + _MINI_SHIM
    Path("core_mini.py").write_text(core, encoding="utf-8")
    print("✅ core_mini.py (pandas -> csvシム)")

    web = Path("web_app.py").read_text(encoding="utf-8")
    web = _replace_once(
        web,
        "from core import (",
        "from core_mini import (",
        "web_app import",
    )
    Path("web_app_mini.py").write_text(web, encoding="utf-8")
    print("✅ web_app_mini.py")

    run = Path("run_app.py").read_text(encoding="utf-8")
    run = _replace_once(
        run,
        "from web_app import app, init_dialogue_system",
        "from web_app_mini import app, init_dialogue_system",
        "run_app import",
    )
    # onefile展開先をカレントに (同梱データへの相対パス解決用・ミニ版のみ)
    run = _replace_once(
        run,
        "current_dir = Path(__file__).parent.absolute()",
        "import os as _os\n\n"
        'if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):\n'
        "    _os.chdir(sys._MEIPASS)\n"
        "current_dir = Path(__file__).parent.absolute()",
        "run_mini meipass",
    )
    Path(ENTRY).write_text(run, encoding="utf-8")
    print(f"✅ {ENTRY}\n")


def check_environment() -> bool:
    print("=== 環境確認 ===\n")
    if sys.version_info < (3, 10):
        print("❌ Python 3.10以上が必要です")
        return False
    print(f"✅ Python: {sys.version.split()[0]}")

    for src in ["core_mini.py", "web_app_mini.py", ENTRY]:
        if not os.path.exists(src):
            print(f"❌ ありません: {src}")
            return False
    for data in DATA_FILES:
        if not os.path.exists(data):
            print(f"❌ データがありません: {data}")
            return False
    print("✅ ミニ版・データの確認通過")

    try:
        import PyInstaller  # noqa: F401

        print(f"✅ PyInstallerあり")
    except ImportError:
        print("PyInstallerをインストールしています...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )
    return True


def build_package() -> bool:
    print("\n=== ミニ版パッケージング開始 ===\n")
    sep = ";" if os.name == "nt" else ":"
    os_name = platform.system()
    print(f"OS: {os_name} (add-data区切り: '{sep}')")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--name",
        APP_NAME,
        "--windowed",
        "--onefile",
        ENTRY,
    ]
    for data in DATA_FILES:
        cmd += ["--add-data", f"{data}{sep}{DATA_DEST}"]
    for mod in EXCLUDE_MODULES:
        cmd += ["--exclude-module", mod]

    print("除外モジュール:", ", ".join(EXCLUDE_MODULES))
    print("同梱データ:", ", ".join(DATA_FILES) + "\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ パッケージング失敗: {e}")
        return False

    exe = Path("dist") / (APP_NAME + (".exe" if os_name == "Windows" else ""))
    if not exe.exists():
        print(f"\n❌ 実行ファイルがありません: {exe}")
        return False
    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"\n✅ パッケージング成功: {exe} ({size_mb:.1f} MB)")
    return True


def main() -> int:
    print("ChatKaltsit ミニ版パッケージツール\n")
    generate_mini_modules()
    if not check_environment():
        sys.exit(1)
    if not build_package():
        sys.exit(1)
    print("\n実行方法: dist/KaltsitAI-mini" + (" (dist内で)" if os.name != "nt" else ""))
    print("※ APIキーは実行環境の環境変数から読みます")

    for specs in glob.glob('*.spec', recursive=True):
        os.remove(specs)
    os.remove('core_mini.py')
    os.remove('web_app_mini.py')
    os.remove('run_mini.py')
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
