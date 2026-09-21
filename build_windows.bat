@echo off
REM -*- coding: utf-8 -*-
chcp 65001 >nul

setlocal enabledelayedexpansion

echo === ChatKaltsit Windowsパッケージツール ===
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Pythonが見つかりません
    echo Python 3.10以上を先にインストールしてください
    echo ダウンロード: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Pythonを確認しました
python --version
echo.

echo PyInstallerをインストールしています...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo [エラー] PyInstallerのインストールに失敗しました
    pause
    exit /b 1
)

echo [OK] PyInstallerのインストール完了
echo.

echo 以前のビルドファイルを掃除しています...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo [OK] 掃除完了
echo.

echo パッケージング開始...
echo 数分かかる場合があります。そのままお待ちください...
echo.

pyinstaller --clean ^
    --name "KaltsitAI" ^
    --windowed ^
    --onefile ^
    --add-data "data;data" ^
    --hidden-import flask ^
    --hidden-import pandas ^
    --hidden-import janome ^
    --hidden-import requests ^
    --hidden-import matplotlib ^
    --hidden-import numpy ^
    --hidden-import dotenv ^
    --exclude-module matplotlib.backends.backend_qt4agg ^
    --exclude-module matplotlib.backends.backend_tkagg ^
    --exclude-module matplotlib.backends.backend_gtk3agg ^
    run_app.py

if %errorlevel% neq 0 (
    echo.
    echo [エラー] パッケージングに失敗しました
    echo 上のエラーメッセージを確認してください
    pause
    exit /b 1
)

if exist "dist\KaltsitAI.exe" (
    echo.
    echo [OK] パッケージング成功！
    echo.
    echo 実行ファイル: %CD%\dist\KaltsitAI.exe
    echo.

    echo @echo off > "dist\ケルシー起動.bat"
    echo chcp 65001 ^>nul >> "dist\ケルシー起動.bat"
    echo cd /d "%%~dp0" >> "dist\ケルシー起動.bat"
    echo echo ChatKaltsit を起動しています... >> "dist\ケルシー起動.bat"
    echo KaltsitAI.exe >> "dist\ケルシー起動.bat"
    echo if errorlevel 1 ( >> "dist\ケルシー起動.bat"
    echo     echo. >> "dist\ケルシー起動.bat"
    echo     echo プログラムが終了しました。何かキーを押してウィンドウを閉じてください... >> "dist\ケルシー起動.bat"
    echo     pause ^>nul >> "dist\ケルシー起動.bat"
    echo ) >> "dist\ケルシー起動.bat"

    echo ChatKaltsit 使い方 > "dist\使い方.txt"
    echo. >> "dist\使い方.txt"
    echo 1. 「ケルシー起動.bat」または「KaltsitAI.exe」をダブルクリック >> "dist\使い方.txt"
    echo 2. ブラウザが自動で http://localhost:8080 を開きます >> "dist\使い方.txt"
    echo 3. 自動で開かない場合は手動で http://localhost:8080 にアクセス >> "dist\使い方.txt"
    echo 4. Ctrl+C でサーバーを停止 >> "dist\使い方.txt"
    echo. >> "dist\使い方.txt"
    echo トラブルシューティング: >> "dist\使い方.txt"
    echo - ポート8080が使用中の場合は、そのプログラムを終了してください >> "dist\使い方.txt"
    echo - Webページにアクセスできない場合はファイアウォール設定を確認してください >> "dist\使い方.txt"
    echo - プログラムが異常終了した場合はターミナルのエラーメッセージを確認してください >> "dist\使い方.txt"

    echo.
    echo [OK] 起動スクリプトと説明ファイルを作成しました
    echo.
    echo 出力ファイル:
    echo   - 実行ファイル: dist\KaltsitAI.exe
    echo   - 起動スクリプト: dist\ケルシー起動.bat
    echo   - 使い方: dist\使い方.txt
    echo.
    echo 使い方:
    echo   方法1: 「ケルシー起動.bat」をダブルクリック ^(推奨^)
    echo   方法2: KaltsitAI.exeをダブルクリック
    echo.

    set /p run_now="今すぐアプリを実行しますか？(y/n): "
    if /i "%run_now%"=="y" (
        echo.
        echo アプリを起動しています...
        start "" "dist\KaltsitAI.exe"
    )
) else (
    echo.
    echo [エラー] パッケージングに失敗しました。実行ファイルが見つかりません
    echo 上のエラーメッセージを確認してください
    pause
    exit /b 1
)

echo.
echo 何かキーを押して終了...
pause >nul
