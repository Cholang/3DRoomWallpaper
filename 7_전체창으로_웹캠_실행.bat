@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
echo 모니터 해상도 크기의 창 + 웹캠 추적. ESC 로 종료.
".venv\Scripts\python.exe" -m room3d
if errorlevel 1 pause
