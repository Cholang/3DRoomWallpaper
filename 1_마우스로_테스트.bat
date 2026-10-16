@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
echo 마우스를 움직이면 시점이 바뀝니다. ESC 로 종료.
".venv\Scripts\python.exe" -m room3d --windowed --mouse
if errorlevel 1 pause
