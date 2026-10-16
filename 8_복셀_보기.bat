@echo off
chcp 65001 >nul
call "%~dp0_setup.bat" || exit /b 1
cd /d "%~dp0"
set "VOX=%~1"
if "%VOX%"=="" set "VOX=assets\sample_village.vox"
echo %VOX% 를 방 안에 띄웁니다 + 웹캠 추적. ESC 로 종료.
echo ^(.vox 파일을 이 bat 파일 위로 끌어다 놓으면 그 파일을 엽니다^)
".venv\Scripts\python.exe" -m room3d "%VOX%"
if errorlevel 1 pause
