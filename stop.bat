@echo off
REM Stop everything started by start.bat (dashboard + bot), no leftover windows
cd /d "%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'Name = ''python.exe''' | Where-Object { $_.CommandLine -like '*uvicorn app.dashboard*' -or $_.CommandLine -like '*run_bot*' -or $_.CommandLine -like '*app.bot*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
del "bot.pid" >nul 2>&1
echo Stopped: dashboard + bot killed, no windows left.
pause
