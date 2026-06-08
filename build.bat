@echo off
chcp 65001 >nul 2>&1
setlocal

set PROJECT_ROOT=%~dp0
cd /d %PROJECT_ROOT%

echo ========================================
echo   YOLOv8 Security - Build
echo ========================================
echo.

:: Step 1: Build frontend
echo [1/3] Building frontend...
cd /d "%PROJECT_ROOT%web"
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed
    exit /b 1
)
echo.

:: Step 2: Copy frontend dist into server directory
echo [2/3] Copying frontend dist to server/web/dist/...
cd /d "%PROJECT_ROOT%"
if exist server\web\dist rmdir /s /q server\web\dist
mkdir server\web\dist 2>nul
xcopy /E /Y /Q web\dist\* server\web\dist\ >nul
if errorlevel 1 (
    echo ERROR: Failed to copy frontend dist
    exit /b 1
)
echo    Done - server/web/dist/ updated
echo.

:: Step 3: Build Java WAR
echo [3/3] Building Java WAR...
cd /d "%PROJECT_ROOT%server"
call mvn clean package -Dmaven.test.skip=true -q
if errorlevel 1 (
    echo ERROR: Maven build failed
    exit /b 1
)
echo.

set WAR_FILE=target\yolov8-security.war

echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo   WAR: server\%WAR_FILE%
echo   Frontend: server\web\dist\
echo.

:: Create deploy directory
cd /d "%PROJECT_ROOT%"
if exist deploy-pkg rmdir /s /q deploy-pkg
mkdir deploy-pkg
mkdir deploy-pkg\detection

copy /Y server\%WAR_FILE% deploy-pkg\app.war >nul
xcopy /E /Y /Q server\web\dist deploy-pkg\web-dist\ >nul
if exist .env (
    copy /Y .env deploy-pkg\.env >nul
) else (
    copy /Y deploy\.env.example deploy-pkg\.env >nul
    echo   WARNING: No .env found, using .env.example
)
if exist detection\cameras.json (
    copy /Y detection\cameras.json deploy-pkg\detection\cameras.json >nul
)

echo   Deploy package contents:
dir /b deploy-pkg\
echo.

for %%f in (deploy-pkg\app.war) do echo   WAR size: %%~zf bytes
echo.
echo ========================================
echo   Deploy Commands
echo ========================================
echo.
echo   1. Upload to server:
echo      scp -r deploy-pkg/* root@YOUR_SERVER_IP:/opt/yolov8-security/
echo.
echo   2. SSH to server and run:
echo      cd /opt/yolov8-security
echo      bash deploy/deploy.sh
echo.
echo   3. Open in browser:
echo      http://YOUR_SERVER_IP:5000
echo.

endlocal
