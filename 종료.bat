@echo off
chcp 65001 >nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object { $_.CommandLine -like '*room3d*' } | ForEach-Object { Stop-Process -Id $_.ProcessId }"
echo room3d 를 종료했습니다.
timeout /t 2 >nul
