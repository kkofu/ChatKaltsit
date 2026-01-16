@echo off
REM -*- coding: utf-8 -*-
REM
REM 普瑞赛斯AI助手 - Windows打包脚本
REM 使用PyInstaller打包为Windows可执行文件
REM

setlocal enabledelayedexpansion

echo === 普瑞赛斯AI助手 - Windows打包工具 ===
echo.

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python
    echo 请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [成功] Python已安装
python --version
echo.

REM 安装PyInstaller
echo 正在安装PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo [错误] PyInstaller安装失败
    pause
    exit /b 1
)

echo [成功] PyInstaller安装完成
echo.

REM 清理之前的构建
echo 清理之前的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo [成功] 清理完成
echo.

REM 运行PyInstaller
echo 开始打包...
echo 这可能需要几分钟时间，请耐心等待...
echo.

pyinstaller --clean ^
    --name "PresetAI" ^
    --windowed ^
    --onefile ^
    --add-data "preset_ai_assistant;preset_ai_assistant" ^
    --add-data ".env;." ^
    --hidden-import flask ^
    --hidden-import pandas ^
    --hidden-import jieba ^
    --hidden-import requests ^
    --hidden-import matplotlib ^
    --hidden-import numpy ^
    --hidden-import dotenv ^
    --hidden-import optimized_response_generator ^
    --exclude-module matplotlib.backends.backend_qt4agg ^
    --exclude-module matplotlib.backends.backend_tkagg ^
    --exclude-module matplotlib.backends.backend_gtk3agg ^
    run_app.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败
    echo 请检查上面的错误信息
    pause
    exit /b 1
)

REM 检查打包结果
if exist "dist\PresetAI.exe" (
    echo.
    echo [成功] 打包成功！
    echo.
    echo 可执行文件位置: %CD%\dist\PresetAI.exe
    echo.
    
    REM 创建启动脚本
    echo @echo off > "dist\启动普瑞赛斯助手.bat"
    echo cd /d "%%~dp0" >> "dist\启动普瑞赛斯助手.bat"
    echo echo 正在启动普瑞赛斯AI助手... >> "dist\启动普瑞赛斯助手.bat"
    echo PresetAI.exe >> "dist\启动普瑞赛斯助手.bat"
    echo if errorlevel 1 ( >> "dist\启动普瑞赛斯助手.bat"
    echo     echo. >> "dist\启动普瑞赛斯助手.bat"
    echo     echo 程序已退出，请按任意键关闭窗口... >> "dist\启动普瑞赛斯助手.bat"
    echo     pause ^>nul >> "dist\启动普瑞赛斯助手.bat"
    echo ) >> "dist\启动普瑞赛斯助手.bat"
    
    REM 创建README
    echo 普瑞赛斯AI助手 - 使用说明 > "dist\使用说明.txt"
    echo. >> "dist\使用说明.txt"
    echo 1. 双击运行 "启动普瑞赛斯助手.bat" 或 "PresetAI.exe" >> "dist\使用说明.txt"
    echo 2. 浏览器会自动打开 http://localhost:8080 >> "dist\使用说明.txt"
    echo 3. 如果浏览器没有自动打开，手动访问 http://localhost:8080 >> "dist\使用说明.txt"
    echo 4. 按 Ctrl+C 停止服务器 >> "dist\使用说明.txt"
    echo. >> "dist\使用说明.txt"
    echo 故障排除: >> "dist\使用说明.txt"
    echo - 如果端口8080被占用，请关闭占用该端口的程序 >> "dist\使用说明.txt"
    echo - 如果无法访问网页，请检查防火墙设置 >> "dist\使用说明.txt"
    echo - 如果程序崩溃，请查看终端中的错误信息 >> "dist\使用说明.txt"
    
    echo.
    echo [成功] 创建启动脚本和说明文件
    echo.
    echo 输出文件:
    echo   - 可执行文件: dist\PresetAI.exe
    echo   - 启动脚本: dist\启动普瑞赛斯助手.bat
    echo   - 使用说明: dist\使用说明.txt
    echo.
    echo 使用方法:
    echo   方法1: 双击运行 "启动普瑞赛斯助手.bat" ^(推荐^)
    echo   方法2: 双击运行 PresetAI.exe
    echo.
    
    REM 询问是否运行
    set /p run_now="是否现在运行应用？(y/n): "
    if /i "%run_now%"=="y" (
        echo.
        echo 正在启动应用...
        start "" "dist\PresetAI.exe"
    )
) else (
    echo.
    echo [错误] 打包失败，未找到可执行文件
    echo 请检查上面的错误信息
    pause
    exit /b 1
)

echo.
echo 按任意键退出...
pause >nul