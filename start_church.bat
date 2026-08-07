@echo off
cd /d "C:\Users\KOJO BOYE\Desktop\ag-cms"
netstat -an | findstr ":5000" | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo AG CMS is already running.
    start "" http://127.0.0.1:5000
) else (
    echo Starting AG CMS...
    start "" http://127.0.0.1:5000
    .venv\Scripts\python.exe run.py
)
echo.
echo Press any key to close this window.
pause >nul
