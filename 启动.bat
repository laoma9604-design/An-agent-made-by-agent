@echo off
chcp 65001 >nul
title Herrs
cd /d %~dp0

echo   ⚡ Herrs 启动中...
python main.py
echo.
echo   Herrs 已关闭
pause
