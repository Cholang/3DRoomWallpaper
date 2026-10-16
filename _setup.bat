@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto :ready

set PYV=
for %%v in (3.12 3.11 3.10) do (
  if not defined PYV (
    py -%%v -c "import sys" >nul 2>&1 && set PYV=%%v
  )
)
if not defined PYV (
  echo [오류] Python 3.10~3.12 가 필요합니다. https://www.python.org/downloads/ 에서 설치해 주세요.
  echo        설치 시 "Add python.exe to PATH" 를 체크하세요. ^(MediaPipe 는 3.13 미지원^)
  pause
  exit /b 1
)
echo Python %PYV% 로 가상환경을 만듭니다...
py -%PYV% -m venv .venv || (pause & exit /b 1)
echo 필요한 패키지를 설치합니다 ^(처음 한 번만, 몇 분 걸립니다^)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo [오류] 설치 실패 & pause & exit /b 1)

:ready
exit /b 0
