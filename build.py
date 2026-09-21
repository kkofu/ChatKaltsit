#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汎用パッケージングスクリプト
WindowsとmacOSの自動パッケージに対応
"""

import os
import sys
import platform
import subprocess
import pathlib as pathlib_module

try:
    from pathlib import Path
except ImportError:
    Path = pathlib_module.Path


def check_environment():
    print("=== ChatKaltsit 環境確認 ===\n")

    python_version = sys.version_info
    if python_version < (3, 10):
        print(f"❌ Pythonバージョンが古すぎます: {python_version.major}.{python_version.minor}")
        print("Python 3.10以上が必要です")
        return False

    print(
        f"✅ Pythonバージョン: {python_version.major}.{python_version.minor}.{python_version.micro}"
    )

    required_files = [
        "web_app.py",
        "run_app.py",
        "requirements.txt",
    ]

    required_dirs = ["data"]

    missing_files = []
    missing_dirs = []

    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)

    if missing_files or missing_dirs:
        print("\n❌ 必要ファイルまたはディレクトリがありません:")
        for file in missing_files:
            print(f"   - {file}")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}")
        return False

    print("✅ 必要ファイルの確認通過")

    try:
        import PyInstaller

        print(f"✅ PyInstallerインストール済み: {PyInstaller.__version__}")
    except ImportError:
        print("⚠️  PyInstallerが未インストールです")
        return False

    return True


def install_dependencies():
    print("\n=== パッケージ依存のインストール ===\n")

    print("アプリ依存をインストールしています...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("PyInstallerをインストールしています...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("\n✅ 依存のインストール完了")


def build_package():
    print("\n=== パッケージング開始 ===\n")

    os_name = platform.system()
    print(f"OS: {os_name}")

    sep = ";" if os_name == "Windows" else ":"

    pyinstaller_cmd = [
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
        "--hidden-import",
        "flask",
        "--hidden-import",
        "pandas",
        "--hidden-import",
        "janome",
        "--hidden-import",
        "requests",
        "--hidden-import",
        "matplotlib",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "dotenv",
        "--exclude-module",
        "matplotlib.backends.backend_qt4agg",
        "--exclude-module",
        "matplotlib.backends.backend_tkagg",
        "--exclude-module",
        "matplotlib.backends.backend_gtk3agg",
        "run_app.py",
    ]

    if os_name == "Darwin":
        pyinstaller_cmd.extend(
            ["--exclude-module", "matplotlib.backends.backend_macosx"]
        )

    print("PyInstallerを実行しています...")
    print("数分かかる場合があります。そのままお待ちください...\n")

    try:
        result = subprocess.run(pyinstaller_cmd, check=True)

        if result.returncode == 0:
            print("\n✅ パッケージング成功！")
            print(f"\n出力ディレクトリ: {Path('dist').absolute()}")
            return True
        else:
            print("\n❌ パッケージング失敗")
            return False

    except subprocess.CalledProcessError as e:
        print(f"\n❌ パッケージング失敗: {e}")
        return False
    except Exception as e:
        print(f"\n❌ パッケージング中にエラー: {e}")
        return False


def create_launch_scripts():
    print("\n=== 起動スクリプト作成 ===\n")

    os_name = platform.system()
    dist_dir = Path("dist")

    if os_name == "Windows":
        script_content = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ChatKaltsit を起動しています...
echo.
KaltsitAI.exe
if errorlevel 1 (
    echo.
    echo プログラムが終了しました。何かキーを押してウィンドウを閉じてください...
    pause >nul
)
"""
        script_path = dist_dir / "ケルシー起動.bat"
        with open(script_path, "w", encoding="cp932") as f:
            f.write(script_content)
        print(f"✅ 作成: {script_path}")

        readme_content = """ChatKaltsit - 使い方

1. 「ケルシー起動.bat」(推奨)または「KaltsitAI.exe」をダブルクリック
2. ブラウザが自動で http://localhost:8080 を開きます
3. 自動で開かない場合は手動で http://localhost:8080 にアクセス
4. Ctrl+C でサーバーを停止

トラブルシューティング:
- ポート8080が使用中の場合は、そのプログラムを終了してください
- Webページにアクセスできない場合はファイアウォール設定を確認してください
- プログラムが異常終了した場合はターミナルのエラーメッセージを確認してください
"""
        readme_path = dist_dir / "使い方.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print(f"✅ 作成: {readme_path}")

    elif os_name == "Darwin":
        script_content = """#!/bin/bash
cd "$(dirname "$0")"
echo "ChatKaltsit を起動しています..."
./KaltsitAI
"""
        script_path = dist_dir / "run_kaltsit.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        print(f"✅ 作成: {script_path}")


def test_package():
    print("\n=== パッケージ結果のテスト ===\n")

    os_name = platform.system()
    dist_dir = Path("dist")

    if os_name == "Windows":
        exe_path = dist_dir / "KaltsitAI.exe"
    else:
        exe_path = dist_dir / "KaltsitAI"

    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ 実行ファイルあり: {exe_path}")
        print(f"   サイズ: {file_size:.2f} MB")
        return True
    else:
        print(f"❌ 実行ファイルがありません: {exe_path}")
        return False


def main():
    print("ChatKaltsit 自動パッケージツール\n")

    if not check_environment():
        print("\n環境確認に失敗したため、依存をインストールします...")
        install_dependencies()

        if not check_environment():
            print("\n❌ 環境構築に失敗しました。依存を手動で確認してください")
            try:
                input("Enterキーで終了...")
            except EOFError:
                pass
            sys.exit(1)

    if not build_package():
        print("\n❌ パッケージング失敗")
        try:
            input("Enterキーで終了...")
        except EOFError:
            pass
        sys.exit(1)

    create_launch_scripts()

    if not test_package():
        print("\n⚠️  パッケージングは完了しましたが検証に失敗しました")

    print("\n" + "=" * 50)
    print("🎉 パッケージング完了！")
    print("=" * 50)
    print(f"\n出力ディレクトリ: {Path('dist').absolute()}")

    os_name = platform.system()
    if os_name == "Windows":
        print("\n使い方:")
        print("  1. 「ケルシー起動.bat」をダブルクリック")
        print("  2. または直接「KaltsitAI.exe」を実行")
    elif os_name == "Darwin":
        print("\n使い方:")
        print("  1. 「KaltsitAI」をダブルクリック")
        print("  2. またはターミナルで './KaltsitAI' を実行")
        print("  3. または './run_kaltsit.sh' を実行")

    print("\nブラウザが自動で http://localhost:8080 を開きます")
    print("=" * 50 + "\n")

    try:
        input("Enterキーで終了...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
