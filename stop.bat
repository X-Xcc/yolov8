@echo off
chcp 65001 >nul 2>&1

echo.
echo   Stopping YOLOv8 Security System...
echo.

:: Kill by port
for %%p in (5000 5001 5173) do (
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr "LISTENING" ^| findstr ":%%p "') do (
        echo   Killing PID %%a (port %%p)
        taskkill /PID %%a /F >nul 2>&1
    )
)

:: Kill detection Python process
echo   Killing Python detection processes...
taskkill /FI "WINDOWTITLE eq Detection*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /F >nul 2>&1

:: Fallback: kill java/python/node spawned by this project
wmic process where "name='java.exe' and commandline like '%%spring-boot%%'" delete 2>nul
wmic process where "name='python.exe' and commandline like '%%yolov8_security%%'" delete 2>nul

echo   Done.
echo.
pause
