@echo off
chcp 65001 >nul
title Herrs 一键安装
cd /d %~dp0

echo.
echo   ⚡ Herrs — 一键安装
echo   ====================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] 没找到 Python
    echo   先去 https://www.python.org/downloads/ 装 3.10+
    echo   装的时候勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo   [OK] Python:
python --version
echo.

echo   [..] pip 安装依赖...
echo   ========================================

:: pip 也走代理（如果系统有的话）
set PIP_PROXY=
if defined HTTPS_PROXY set PIP_PROXY=%HTTPS_PROXY%
if defined https_proxy set PIP_PROXY=%https_proxy%
if not "%PIP_PROXY%"=="" (
    echo   检测到代理: %PIP_PROXY%
    pip install -r requirements.txt --proxy %PIP_PROXY%
) else (
    pip install -r requirements.txt
)

echo   ========================================
if %errorlevel% neq 0 (
    echo.
    echo   [FAIL] 装依赖失败了
    echo   检查网络 / 代理 / pip 版本
    pause
    exit /b 1
)

echo.
echo   [OK] 依赖装好了
echo.

if not exist herrs_config.json (
    echo   还没有 API Key，启动后点右上角 ^🔑 设置
    echo.
)

echo   现在可以双击 启动.bat 了
pause
