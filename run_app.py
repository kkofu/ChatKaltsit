#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import webbrowser
import time
import threading
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def check_environment():
    print("=== ケルシーAI対話アシスタント ===")
    print("初期化中...")

    # データディレクトリ確認
    data_dir = current_dir / "data"
    if not data_dir.exists():
        print(f"❌ データディレクトリが存在しません: {data_dir}")
        print("必要なデータファイルが含まれているか確認してください")
        return False

    # 対話データ確認
    dialogues_file = data_dir / "kaltsit_dialogues.csv"
    if not dialogues_file.exists():
        print(f"❌ 対話データファイルが存在しません: {dialogues_file}")
        return False

    print("✅ 環境チェック通過")
    return True


def open_browser():
    time.sleep(1)
    webbrowser.open("http://localhost:8080")


def main():
    if not check_environment():
        input("Enterキーで終了...")
        sys.exit(1)

    try:
        from web_app import app, init_dialogue_system

        # 対話システム初期化
        init_dialogue_system()

        print("\n" + "=" * 50)
        print("サーバー起動成功")
        print("=" * 50)
        print("\nアクセス先:")
        print("  - http://localhost:8080")
        print("  - http://127.0.0.1:8080")
        print("\nCtrl+C でサーバー停止")
        print("=" * 50 + "\n")

        # バックグラウンドスレッドでブラウザを開く
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()

        # Flaskアプリ起動
        app.run(host="0.0.0.0", port=8080, debug=False)

    except KeyboardInterrupt:
        print("\n\nサーバーを停止しました")
    except Exception as e:
        print(f"\n❌ 起動失敗: {e}")
        import traceback

        traceback.print_exc()
        input("Enterキーで終了...")
        sys.exit(1)


if __name__ == "__main__":
    main()
