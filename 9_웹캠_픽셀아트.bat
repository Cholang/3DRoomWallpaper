@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
echo 웹캠 영상을 픽셀 아트로 보여줍니다. ESC 로 종료.
".venv\Scripts\python.exe" -m room3d.pixelcam
if errorlevel 1 pause
