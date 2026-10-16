@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
echo 바탕화면 뒤에 실행합니다. 종료하려면 작업 관리자에서 python.exe 를 끝내세요.
".venv\Scripts\python.exe" -m room3d --wallpaper
if errorlevel 1 pause
