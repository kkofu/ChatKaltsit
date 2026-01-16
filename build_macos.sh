#!/bin/bash
# -*- coding: utf-8 -*-
"""
macOS打包脚本
使用PyInstaller打包为macOS应用程序
"""

set -e  # 遇到错误立即退出

echo "=== 普瑞赛斯AI助手 - macOS打包工具 ==="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到Python3${NC}"
    echo "请先安装Python 3.7或更高版本"
    exit 1
fi

echo -e "${GREEN}✅ Python3已安装${NC}"

# 安装PyInstaller
echo ""
echo "正在安装PyInstaller..."
pip3 install pyinstaller

# 清理之前的构建
echo ""
echo "清理之前的构建文件..."
rm -rf build dist *.spec

# 运行PyInstaller
echo ""
echo "开始打包..."
echo "这可能需要几分钟时间，请耐心等待..."
echo ""

pyinstaller --clean \
    --name "PresetAI" \
    --windowed \
    --onefile \
    --add-data "preset_ai_assistant:preset_ai_assistant" \
    --add-data ".env:." \
    --hidden-import flask \
    --hidden-import pandas \
    --hidden-import jieba \
    --hidden-import requests \
    --hidden-import matplotlib \
    --hidden-import numpy \
    --hidden-import dotenv \
    --hidden-import optimized_response_generator \
    --exclude-module matplotlib.backends.backend_qt4agg \
    --exclude-module matplotlib.backends.backend_tkagg \
    --exclude-module matplotlib.backends.backend_gtk3agg \
    --exclude-module matplotlib.backends.backend_macosx \
    run_app.py

# 检查打包结果
if [ -f "dist/PresetAI" ]; then
    echo ""
    echo -e "${GREEN}✅ 打包成功！${NC}"
    echo ""
    echo "应用程序位置: $(pwd)/dist/PresetAI"
    echo ""
    
    # 创建应用程序包结构
    APP_NAME="PresetAI.app"
    APP_PATH="dist/$APP_NAME"
    
    echo "正在创建macOS应用程序包..."
    rm -rf "$APP_PATH"
    
    # 创建应用目录结构
    mkdir -p "$APP_PATH/Contents/MacOS"
    mkdir -p "$APP_PATH/Contents/Resources"
    
    # 创建Info.plist
    cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>PresetAI</string>
    <key>CFBundleIdentifier</key>
    <string>com.presetai.assistant</string>
    <key>CFBundleName</key>
    <string>PresetAI</string>
    <key>CFBundleDisplayName</key>
    <string>普瑞赛斯AI助手</string>
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
    
    # 复制可执行文件
    cp "dist/PresetAI" "$APP_PATH/Contents/MacOS/"
    
    # 创建一个简单的启动脚本
    cat > "dist/run_preset_ai.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./PresetAI
EOF
    chmod +x "dist/run_preset_ai.sh"
    
    echo -e "${GREEN}✅ 应用程序包创建成功！${NC}"
    echo ""
    echo "输出文件:"
    echo "  - 可执行文件: dist/PresetAI"
    echo "  - 启动脚本: dist/run_preset_ai.sh"
    echo "  - 应用包: dist/PresetAI.app"
    echo ""
    echo "使用方法:"
    echo "  方法1: 双击运行 dist/PresetAI"
    echo "  方法2: 在终端中运行 ./dist/run_preset_ai.sh"
    echo "  方法3: 拖拽PresetAI.app到应用程序文件夹"
    echo ""
    
    # 询问是否运行
    read -p "是否现在运行应用？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在启动应用..."
        "./dist/PresetAI"
    fi
else
    echo ""
    echo -e "${RED}❌ 打包失败${NC}"
    echo "请检查上面的错误信息"
    exit 1
fi