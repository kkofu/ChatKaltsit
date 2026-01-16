#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用打包脚本
支持Windows和macOS的自动打包
"""

import os
import sys
import platform
import subprocess
import pathlib as pathlib_module

try:
    from pathlib import Path
except ImportError:
    # 对于老版本Python
    Path = pathlib_module.Path


def check_environment():
    """检查打包环境"""
    print("=== 普瑞赛斯AI助手 - 环境检查 ===\n")

    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 7):
        print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
        print("需要Python 3.7或更高版本")
        return False

    print(
        f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}"
    )

    # 检查必要文件
    required_files = [
        "preset_ai_assistant.py",
        "run_app.py",
        "requirements.txt",
        ".env",
    ]

    required_dirs = ["preset_ai_assistant"]

    missing_files = []
    missing_dirs = []

    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)

    if missing_files or missing_dirs:
        print("\n❌ 缺少必要文件或目录:")
        for file in missing_files:
            print(f"   - {file}")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}")
        return False

    print("✅ 必要文件检查通过")

    # 检查PyInstaller
    try:
        import PyInstaller

        print(f"✅ PyInstaller已安装: {PyInstaller.__version__}")
    except ImportError:
        print("⚠️  PyInstaller未安装")
        return False

    return True


def install_dependencies():
    """安装打包依赖"""
    print("\n=== 安装打包依赖 ===\n")

    # 安装requirements.txt中的依赖
    print("安装应用依赖...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 安装PyInstaller
    print("安装PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("\n✅ 依赖安装完成")


def build_package():
    """执行打包"""
    print("\n=== 开始打包 ===\n")

    # 检测操作系统
    os_name = platform.system()
    print(f"操作系统: {os_name}")

    # 构建PyInstaller命令
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--name",
        "PresetAI",
        "--windowed",
        "--onefile",
        "--add-data",
        "preset_ai_assistant;preset_ai_assistant",
        "--add-data",
        ".env;.",
        "--hidden-import",
        "flask",
        "--hidden-import",
        "pandas",
        "--hidden-import",
        "jieba",
        "--hidden-import",
        "requests",
        "--hidden-import",
        "matplotlib",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "dotenv",
        "--hidden-import",
        "optimized_response_generator",
        "--exclude-module",
        "matplotlib.backends.backend_qt4agg",
        "--exclude-module",
        "matplotlib.backends.backend_tkagg",
        "--exclude-module",
        "matplotlib.backends.backend_gtk3agg",
        "run_app.py",
    ]

    # macOS特定配置
    if os_name == "Darwin":
        pyinstaller_cmd.extend(
            ["--exclude-module", "matplotlib.backends.backend_macosx"]
        )

    print("执行PyInstaller...")
    print("这可能需要几分钟时间，请耐心等待...\n")

    try:
        result = subprocess.run(pyinstaller_cmd, check=True)

        if result.returncode == 0:
            print("\n✅ 打包成功！")
            print(f"\n输出目录: {Path('dist').absolute()}")
            return True
        else:
            print("\n❌ 打包失败")
            return False

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 打包过程出错: {e}")
        return False


def create_launch_scripts():
    """创建启动脚本"""
    print("\n=== 创建启动脚本 ===\n")

    os_name = platform.system()
    dist_dir = Path("dist")

    if os_name == "Windows":
        # 创建Windows批处理脚本
        script_content = """@echo off
cd /d "%~dp0"
echo 正在启动普瑞赛斯AI助手...
echo.
PresetAI.exe
if errorlevel 1 (
    echo.
    echo 程序已退出，请按任意键关闭窗口...
    pause >nul
)
"""
        script_path = dist_dir / "启动普瑞赛斯助手.bat"
        with open(script_path, "w", encoding="gbk") as f:
            f.write(script_content)
        print(f"✅ 创建: {script_path}")

        # 创建使用说明
        readme_content = """普瑞赛斯AI助手 - 使用说明

1. 双击运行 "启动普瑞赛斯助手.bat"（推荐）或 "PresetAI.exe"
2. 浏览器会自动打开 http://localhost:8080
3. 如果浏览器没有自动打开，手动访问 http://localhost:8080
4. 按 Ctrl+C 停止服务器

故障排除:
- 如果端口8080被占用，请关闭占用该端口的程序
- 如果无法访问网页，请检查防火墙设置
- 如果程序崩溃，请查看终端中的错误信息
"""
        readme_path = dist_dir / "使用说明.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print(f"✅ 创建: {readme_path}")

    elif os_name == "Darwin":
        # 创建macOS shell脚本
        script_content = """#!/bin/bash
cd "$(dirname "$0")"
echo "正在启动普瑞赛斯AI助手..."
./PresetAI
"""
        script_path = dist_dir / "run_preset_ai.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        print(f"✅ 创建: {script_path}")


def test_package():
    """测试打包结果"""
    print("\n=== 测试打包结果 ===\n")

    os_name = platform.system()
    dist_dir = Path("dist")

    if os_name == "Windows":
        exe_path = dist_dir / "PresetAI.exe"
    else:
        exe_path = dist_dir / "PresetAI"

    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✅ 可执行文件存在: {exe_path}")
        print(f"   文件大小: {file_size:.2f} MB")
        return True
    else:
        print(f"❌ 可执行文件不存在: {exe_path}")
        return False


def main():
    """主函数"""
    print("🎉 普瑞赛斯AI助手 - 自动打包工具\n")

    # 检查环境
    if not check_environment():
        print("\n环境检查失败，正在安装依赖...")
        install_dependencies()

        # 重新检查
        if not check_environment():
            print("\n❌ 环境配置失败，请手动检查依赖")
            try:
                input("按回车键退出...")
            except EOFError:
                pass
            sys.exit(1)

    # 执行打包
    if not build_package():
        print("\n❌ 打包失败")
        try:
            input("按回车键退出...")
        except EOFError:
            pass
        sys.exit(1)

    # 创建启动脚本
    create_launch_scripts()

    # 测试打包结果
    if not test_package():
        print("\n⚠️  打包完成但验证失败")

    # 总结
    print("\n" + "=" * 50)
    print("🎉 打包完成！")
    print("=" * 50)
    print(f"\n输出目录: {Path('dist').absolute()}")

    os_name = platform.system()
    if os_name == "Windows":
        print("\n使用方法:")
        print("  1. 双击运行 '启动普瑞赛斯助手.bat'")
        print("  2. 或直接运行 'PresetAI.exe'")
    elif os_name == "Darwin":
        print("\n使用方法:")
        print("  1. 双击运行 'PresetAI'")
        print("  2. 或在终端中执行 './PresetAI'")
        print("  3. 或运行 './run_preset_ai.sh'")

    print("\n浏览器会自动打开 http://localhost:8080")
    print("=" * 50 + "\n")

    try:
        input("按回车键退出...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
