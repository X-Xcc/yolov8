@echo off
chcp 936 >nul 2>&1
setlocal

echo.
echo  ===========================================
echo    Stopping YOLOv8 Security System...
echo  ===========================================
echo.

:: Kill Java backend
echo [1/2] Stopping Spring Boot backend...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo    Killed PID %%a
)
taskkill /f /im java.exe /fi "windowtitle eq YOLOv8-Backend*" >nul 2>&1
echo    Done.

:: Kill Python detection
echo [2/2] Stopping Python detection...
taskkill /f /fi "windowtitle eq YOLOv8-Detection*" >nul 2>&1
echo    Done.

echo.
echo  All services stopped.
timeout /t 3 /nobreak >nul
endlocal
