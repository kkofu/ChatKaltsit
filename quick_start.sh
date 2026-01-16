#!/bin/bash
# -*- coding: utf-8 -*-
"""
快速开始脚本 - 帮助用户快速运行普瑞赛斯AI助手
"""

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== 普瑞赛斯AI助手 - 快速开始 ===${NC}"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到Python3${NC}"
    echo "请先安装Python 3.7或更高版本："
    echo "  macOS: brew install python3"
    echo "  或下载: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | head -1)
echo -e "${GREEN}✅ Python版本: $PYTHON_VERSION${NC}"

# 检查.env文件
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  检测到.env文件${NC}"
    echo "如果你还没有配置API密钥，建议使用.env.example作为模板："
    echo "  cp .env.example .env"
    echo ""
fi

# 检查必要文件
required_files=("preset_ai_assistant.py" "preset_ai_assistant/")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ] && [ ! -d "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "${RED}❌ 缺少必要文件:${NC}"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "请先运行以下命令生成必要数据："
    echo "  python extract_preset_dialogues.py"
    echo "  python analyze_preset_language.py"
    exit 1
fi

echo -e "${GREEN}✅ 必要文件检查通过${NC}"
echo ""

# 提供运行选项
echo -e "${BLUE}请选择运行模式:${NC}"
echo ""
echo "1) 🌐 Web界面模式（推荐）"
echo "   启动Web服务器，通过浏览器与普瑞赛斯对话"
echo ""
echo "2) 🔧 API测试模式"
echo "   测试OpenRouter API连接和响应生成"
echo ""
echo "3) 📊 数据分析模式"
echo "   查看角色特征统计和语料信息"
echo ""
echo "4) 🏗  打包模式"
echo "   将程序打包为可执行文件"
echo ""
echo "5) 🧪 开发模式"
echo   重新生成对话数据并进行分析"
echo ""
echo "6) 📖 查看帮助"
echo "   查看所有使用选项"
echo ""
echo "0) 退出"
echo ""

read -p "请输入选项 (0-6): " -n 1 -r

case $REPLY in
    1)
        echo -e "${GREEN}=== 启动Web界面 ===${NC}"
        python3 preset_ai_assistant.py
        ;;
    2)
        echo -e "${GREEN}=== 测试API连接 ===${NC}"
        python3 test_openrouter.py
        ;;
    3)
        echo -e "${GREEN}=== 数据分析 ===${NC}"
        python3 test_packaging.py
        ;;
    4)
        echo -e "${GREEN}=== 打包程序 ===${NC}"
        python3 build_minimal.py
        ;;
    5)
        echo -e "${GREEN}=== 开发模式 ===${NC}"
        echo ""
        echo "重新生成对话数据..."
        python3 extract_preset_dialogues.py
        echo "分析语言特征..."
        python3 analyze_preset_language.py
        echo ""
        echo -e "${GREEN}✅ 开发数据更新完成${NC}"
        echo ""
        echo "是否要启动Web界面？(y/n)"
        read -p "" -n 1 -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 preset_ai_assistant.py
        fi
        ;;
    6)
        echo -e "${BLUE}=== 使用帮助 ===${NC}"
        echo ""
        echo "${YELLOW}Web界面模式:${NC}"
        echo "  - 访问: http://localhost:8080"
        echo "  - 示例话题:"
        echo "    • 你觉得宇宙的本质是什么？"
        echo "    • 为什么我们会存在？"
        echo "    • 什么是真理？"
        echo ""
        echo "${YELLOW}API配置:${NC}"
        echo "  - 环境变量文件: .env"
        echo "  - 配置模板: .env.example"
        echo "  - 主要API: OpenRouter (z-ai/glm-4.5-air:free)"
        echo ""
        echo "${YELLOW}常用命令:${NC}"
        echo "  python3 preset_ai_assistant.py      # 启动Web服务"
        echo "  python3 extract_preset_dialogues.py   # 重新提取对话数据"
        echo "  python3 analyze_preset_language.py    # 重新分析语言特征"
        echo "  python3 build_minimal.py             # 打包程序"
        echo ""
        echo "${YELLOW}故障排除:${NC}"
        echo "  端口冲突: lsof -ti :8080 | xargs kill -9"
        echo "  清理缓存: rm -rf __pycache__"
        echo "  查看日志: tail -f startup.log"
        echo ""
        echo "${YELLOW}配置OpenRouter API:${NC}"
        echo "   1. 访问 https://openrouter.ai/"
        echo "   2. 注册或登录账户"
        echo "   3. 在设置中创建API密钥"
        echo "    4. 复制密钥到.env文件"
        echo "   OPENROUTER_API_KEY=sk-or-v1-..."
        ;;
    0)
        echo "退出..."
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== 完成 ===${NC}"