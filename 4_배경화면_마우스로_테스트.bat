@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
echo 바탕화면 모드 + 마우스 추적. 종료: 작업 관리자에서 python.exe 끝내기.
".venv\Scripts\python.exe" -m room3d --wallpaper --mouse
pause
