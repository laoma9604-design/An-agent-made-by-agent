@echo off
cd /d %~dp0
echo 🔨 正在打包 Herrs Desktop...
pyinstaller --onefile --noconsole --name "Herrs" main.py 2>&1
echo.
echo ✅ 打包完成！exe 在 dist\Herrs.exe
pause
