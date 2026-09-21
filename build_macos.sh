#!/bin/bash
# -*- coding: utf-8 -*-

set -e

echo "=== ChatKaltsit macOSパッケージツール ==="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3が見つかりません${NC}"
    echo "Python 3.10以上を先にインストールしてください"
    exit 1
fi

echo -e "${GREEN}✅ Python3を確認しました${NC}"

echo ""
echo "PyInstallerをインストールしています..."
pip3 install pyinstaller

echo ""
echo "以前のビルドファイルを掃除しています..."
rm -rf build dist *.spec

echo ""
echo "パッケージング開始..."
echo "数分かかる場合があります。そのままお待ちください..."
echo ""

pyinstaller --clean \
    --name "KaltsitAI" \
    --windowed \
    --onefile \
    --add-data "data:data" \
    --hidden-import flask \
    --hidden-import pandas \
    --hidden-import janome \
    --hidden-import requests \
    --hidden-import matplotlib \
    --hidden-import numpy \
    --hidden-import dotenv \
    --exclude-module matplotlib.backends.backend_qt4agg \
    --exclude-module matplotlib.backends.backend_tkagg \
    --exclude-module matplotlib.backends.backend_gtk3agg \
    --exclude-module matplotlib.backends.backend_macosx \
    run_app.py

if [ -f "dist/KaltsitAI" ]; then
    echo ""
    echo -e "${GREEN}✅ パッケージング成功！${NC}"
    echo ""
    echo "アプリケーション: $(pwd)/dist/KaltsitAI"
    echo ""

    APP_NAME="KaltsitAI.app"
    APP_PATH="dist/$APP_NAME"

    echo "macOSアプリケーションパッケージを作成しています..."
    rm -rf "$APP_PATH"

    mkdir -p "$APP_PATH/Contents/MacOS"
    mkdir -p "$APP_PATH/Contents/Resources"

    cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>KaltsitAI</string>
    <key>CFBundleIdentifier</key>
    <string>com.kaltsitai.assistant</string>
    <key>CFBundleName</key>
    <string>KaltsitAI</string>
    <key>CFBundleDisplayName</key>
    <string>ChatKaltsit</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

    cp "dist/KaltsitAI" "$APP_PATH/Contents/MacOS/"

    cat > "dist/run_kaltsit.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./KaltsitAI
EOF
    chmod +x "dist/run_kaltsit.sh"

    echo -e "${GREEN}✅ アプリケーションパッケージの作成成功！${NC}"
    echo ""
    echo "出力ファイル:"
    echo "  - 実行ファイル: dist/KaltsitAI"
    echo "  - 起動スクリプト: dist/run_kaltsit.sh"
    echo "  - アプリパッケージ: dist/KaltsitAI.app"
    echo ""
    echo "使い方:"
    echo "  方法1: dist/KaltsitAI をダブルクリック"
    echo "  方法2: ターミナルで ./dist/run_kaltsit.sh を実行"
    echo "  方法3: KaltsitAI.app をアプリケーションフォルダへドラッグ"
    echo ""

    read -p "今すぐアプリを実行しますか？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "アプリを起動しています..."
        "./dist/KaltsitAI"
    fi
else
    echo ""
    echo -e "${RED}❌ パッケージング失敗${NC}"
    echo "上のエラーメッセージを確認してください"
    exit 1
fi
