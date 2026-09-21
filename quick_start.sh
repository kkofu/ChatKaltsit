#!/bin/bash
# -*- coding: utf-8 -*-

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== ChatKaltsit クイックスタート ===${NC}"
echo ""

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3が見つかりません${NC}"
    echo "Python 3.10以上を先にインストールしてください："
    echo "  macOS: brew install python3"
    echo "  または: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | head -1)
echo -e "${GREEN}✅ Pythonバージョン: $PYTHON_VERSION${NC}"

if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .envファイルを検出しました${NC}"
    echo "APIキーが未設定の場合は .env.example を雛形にしてください："
    echo "  cp .env.example .env"
    echo ""
fi

required_files=("web_app.py" "data/")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ] && [ ! -d "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "${RED}❌ 必要ファイルがありません:${NC}"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "先に以下のコマンドで必要データを生成してください："
    echo "  python extract_kaltsit_dialogues.py"
    echo "  python analyze_kaltsit_language.py"
    exit 1
fi

echo -e "${GREEN}✅ 必要ファイルの確認通過${NC}"
echo ""

echo -e "${BLUE}実行モードを選択してください:${NC}"
echo ""
echo "1) 🌐 Web画面モード（推奨）"
echo "   Webサーバーを起動し、ブラウザでケルシーと対話"
echo ""
echo "2) 🔧 APIテストモード"
echo "   OpenRouter APIの接続と応答生成をテスト"
echo ""
echo "3) 📊 データ分析モード"
echo "   キャラ特徴統計とコーパス情報を表示"
echo ""
echo "4) 🏗  パッケージモード"
echo "   プログラムを実行ファイルにパッケージ"
echo ""
echo "5) 🧪 開発モード"
echo "   対話データを再生成して分析する"
echo ""
echo "6) 📖 ヘルプ表示"
echo "   全使用オプションを表示"
echo ""
echo "0) 終了"
echo ""

read -p "番号を入力 (0-6): " -n 1 -r

case $REPLY in
    1)
        echo -e "${GREEN}=== Web画面を起動 ===${NC}"
        python3 web_app.py
        ;;
    2)
        echo -e "${GREEN}=== API接続をテスト ===${NC}"
        python3 test_openrouter.py
        ;;
    3)
        echo -e "${GREEN}=== データ分析 ===${NC}"
        python3 test_packaging.py
        ;;
    4)
        echo -e "${GREEN}=== プログラムをパッケージ ===${NC}"
        python3 build_minimal.py
        ;;
    5)
        echo -e "${GREEN}=== 開発モード ===${NC}"
        echo ""
        echo "対話データを再生成しています..."
        python3 extract_kaltsit_dialogues.py
        echo "言語特徴を分析しています..."
        python3 analyze_kaltsit_language.py
        echo ""
        echo -e "${GREEN}✅ 開発データの更新完了${NC}"
        echo ""
        echo "Web画面を起動しますか？(y/n)"
        read -p "" -n 1 -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 web_app.py
        fi
        ;;
    6)
        echo -e "${BLUE}=== 使い方 ===${NC}"
        echo ""
        echo "${YELLOW}Web画面モード:${NC}"
        echo "  - アクセス: http://localhost:8080"
        echo "  - 話題の例:"
        echo "    • この作戦についてどう思う？"
        echo "    • 体調が優れないんだ"
        echo "    • ロドスの現状を報告しろ"
        echo ""
        echo "${YELLOW}API設定:${NC}"
        echo "  - 環境変数ファイル: .env"
        echo "  - 設定テンプレート: .env.example"
        echo "  - 主要API: Gemini (gemini-3.8-flash、予備あり)"
        echo "  - 予備API: OpenRouter (無料モデル、フォールバック付き)"
        echo ""
        echo "${YELLOW}よく使うコマンド:${NC}"
        echo "  python3 run_app.py      # Webサーバー起動"
        echo "  python3 chat_cli.py                 # CLIで対話"
        echo "  python3 extract_kaltsit_dialogues.py   # 対話データ再抽出"
        echo "  python3 analyze_kaltsit_language.py    # 言語特徴の再分析"
        echo "  python3 build_minimal.py             # プログラムをパッケージ"
        echo ""
        echo "${YELLOW}トラブルシューティング:${NC}"
        echo "  ポート競合: lsof -ti :8080 | xargs kill -9"
        echo "  キャッシュ掃除: rm -rf __pycache__"
        echo "  ログ確認: tail -f startup.log"
        echo ""
        echo "${YELLOW}Gemini APIの設定:${NC}"
        echo "   1. https://aistudio.google.com/ にアクセス"
        echo "   2. アカウント登録またはログイン"
        echo "   3. APIキーを発行"
        echo "   4. .envファイルに GEMINI_API_KEY=... を記入"
        ;;
    0)
        echo "終了します..."
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 無効な選択です${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== 完了 ===${NC}"
