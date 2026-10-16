@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
echo 모든 창 뒤에 깔리는 배경 모드 + 마우스 추적. 종료는 종료.bat 을 실행하세요.
".venv\Scripts\python.exe" -m room3d --background --mouse
pause
