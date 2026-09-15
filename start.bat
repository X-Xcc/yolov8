@echo off
setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"
set "SEP=  ========================================"

:: ============================================================
::   YOLOv8 Security - One-Click Start
:: ============================================================
:: Usage:
::   start.bat              Build & start all components
::   start.bat --no-python   Skip Python detection
::   start.bat --no-frontend Skip frontend dev server
::   start.bat --no-empty    Skip empty-data backend (port 5001)
::   start.bat --no-build    Skip Maven build (use existing WAR)
::   start.bat --prod        Production mode (built frontend, no Vite)
:: ============================================================

set SKIP_PYTHON=0
set SKIP_FRONTEND=0
set SKIP_EMPTY=0
set SKIP_BUILD=0
set PROD_MODE=0

:parse_args
if "%~1"=="" goto :check_prereqs
if /i "%~1"=="--no-python"   set SKIP_PYTHON=1
if /i "%~1"=="--no-detection" set SKIP_PYTHON=1
if /i "%~1"=="--no-frontend" set SKIP_FRONTEND=1
if /i "%~1"=="--no-empty"    set SKIP_EMPTY=1
if /i "%~1"=="--no-build"    set SKIP_BUILD=1
if /i "%~1"=="--prod"        set PROD_MODE=1
shift
goto :parse_args

:check_prereqs
echo.
echo %SEP%
echo   YOLOv8 Security System
echo %SEP%
echo.

:: --- Java ---
echo   [1/4] Java..
set JAVA_OK=0
for %%e in ("%JAVA_HOME%") do if exist "%%~e\bin\java.exe" set JAVA_OK=1
if !JAVA_OK!==0 where java >nul 2>&1 && set JAVA_OK=1
if !JAVA_OK!==0 (
    echo   [FAIL] Java not found - set JAVA_HOME or add to PATH
    goto :end_error
)
set "JAVA_EXE=!JAVA_HOME!\bin\java.exe"
echo   [OK]   Java: !JAVA_EXE!

:: --- Python ---
echo   [2/4] Python..
set PYTHON_OK=0
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
    set PYTHON_OK=1
) else (
    where python >nul 2>&1 && set PYTHON_EXE=python && set PYTHON_OK=1
)
if !PYTHON_OK!==0 (
    echo   [WARN] Python not found - detection module will be skipped
    set SKIP_PYTHON=1
) else (
    echo   [OK]   Python: !PYTHON_EXE!
)

:: --- Maven ---
echo   [3/4] Maven..
set MVN_OK=0
if exist "%PROJECT_ROOT%server\mvnw.cmd" (
    set "MVN_CMD=%PROJECT_ROOT%server\mvnw.cmd"
    set MVN_OK=1
) else (
    where mvn >nul 2>&1 && set "MVN_CMD=mvn" && set MVN_OK=1
)
if !MVN_OK!==0 (
    echo   [FAIL] Maven not found
    goto :end_error
)
echo   [OK]   Maven: !MVN_CMD!

:: --- Node ---
echo   [4/4] Node..
set NODE_OK=0
where node >nul 2>&1 && set NODE_OK=1
if !NODE_OK!==0 (
    echo   [WARN] Node not found - frontend dev server will be skipped
    set SKIP_FRONTEND=1
) else (
    for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
    echo   [OK]   Node: !NODE_VER!
)

:: --- Port check ---
echo.
echo   Checking ports..
set PORT_CONFLICT=0
for %%p in (5000 5001 5173) do (
    set "FOUND=0"
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%%p " ^| findstr "LISTENING"') do set "FOUND=1"
    if "!FOUND!"=="1" set /a PORT_CONFLICT+=1
)
if !PORT_CONFLICT! gtr 0 (
    echo   [WARN] !PORT_CONFLICT! ports already in use
)

:: ============================================================
::   Build
:: ============================================================
echo.
echo %SEP%
echo   Build
echo %SEP%

set "WAR_FILE=%PROJECT_ROOT%server\target\yolov8-security.war"

if "%SKIP_BUILD%"=="1" goto :check_build_skip
goto :do_build
:check_build_skip
if not exist "%WAR_FILE%" goto :build_anyway
echo   [SKIP] Build skipped, WAR exists
goto :start_components
:build_anyway
echo   [WARN] WAR missing, building anyway
:do_build

if exist "%WAR_FILE%.original" del /f "%WAR_FILE%.original" >nul 2>&1

if not exist "%WAR_FILE%" goto :first_build
echo   [BUILD] Maven package (incremental)..
pushd "%PROJECT_ROOT%server"
call "%MVN_CMD%" package -DskipTests -q
if %errorlevel% neq 0 (
    echo   [WARN] Incremental build failed, retrying with clean..
    call "%MVN_CMD%" clean package -DskipTests -q
)
goto :build_done
:first_build
echo   [BUILD] Maven clean package (first build)..
pushd "%PROJECT_ROOT%server"
call "%MVN_CMD%" clean package -DskipTests -q
:build_done
if %errorlevel% neq 0 (
    popd
    echo   [FAIL] Maven build failed
    goto :end_error
)
popd
echo   [OK]   Build complete

:: ============================================================
::   Start Components
:: ============================================================
:start_components
echo.
echo %SEP%
echo   Starting Components
echo %SEP%
echo.

:: --- Load .env file ---
if exist "%PROJECT_ROOT%.env" (
    echo   Loading .env..
    for /f "usebackq tokens=1,* delims==" %%a in ("%PROJECT_ROOT%.env") do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" if not "%%a"=="" set "%%a=%%b"
    )
)

:: --- CICSIC 聚集复核桥接（YOLO 与 CICSIC 仍是独立服务） ---
if not defined CICSIC_REVIEW_URL set "CICSIC_REVIEW_URL=http://127.0.0.1:8010/api/security-ai/yolo-reviews"
if not defined CICSIC_REVIEW_ENABLED set "CICSIC_REVIEW_ENABLED=true"

set "JAVA_OPTS=-Xmx512m"

:: --- Python Detection ---
if "%SKIP_PYTHON%"=="1" goto :skip_python
echo   [START] Python detection module..
start "Detection" cmd /k "cd /d "%PROJECT_ROOT%detection" && "%PYTHON_EXE%" yolov8_security.py"
echo   [OK]   Detection started in new window
:skip_python

:: --- Java Backend :5000 ---
echo   [START] Java backend (port 5000, live data)..
start "Backend-5000" cmd /k "cd /d "%PROJECT_ROOT%server" && "%JAVA_EXE%" %JAVA_OPTS% -jar target\yolov8-security.war --server.port=5000"
echo   [OK]   Backend started in new window

:: --- Java Backend :5001 ---
if "%SKIP_EMPTY%"=="1" goto :skip_empty
echo   [START] Java backend (port 5001, empty data)..
start "Backend-5001" cmd /k "cd /d "%PROJECT_ROOT%server" && "%JAVA_EXE%" %JAVA_OPTS% -DDATA_DIR=./data_empty -jar target\yolov8-security.war --server.port=5001"
echo   [OK]   Empty-data backend started in new window
:skip_empty

:: --- Frontend ---
if "%SKIP_FRONTEND%"=="1" goto :skip_frontend
if "%PROD_MODE%"=="1" goto :prod_mode

echo   [START] Frontend dev server (port 5173)..
if not exist "%PROJECT_ROOT%web\node_modules" (
    echo   [INFO]  node_modules not found, running npm install first..
    pushd "%PROJECT_ROOT%web" && call npm install && popd
)
start "Frontend-5173" cmd /k "cd /d "%PROJECT_ROOT%web" && npm run dev"
goto :done

:prod_mode
echo   [INFO]  Production mode - frontend served by Java at port 5000
echo   [INFO]  Run build.bat first if you haven't built yet
:skip_frontend

:done
echo.
echo %SEP%
echo   All Components Started
echo %SEP%
echo.
echo     Detection  :  Python window (if not skipped)
echo     Backend    :  http://localhost:5000 (live data)
echo     Backend    :  http://localhost:5001 (empty data, if not skipped)
if "%SKIP_FRONTEND%"=="0" if "%PROD_MODE%"=="0" echo     Frontend   :  http://localhost:5173
echo     Login      :  http://localhost:5000  (production)
echo                  http://localhost:5173   (dev)
echo.
echo   Close individual windows to stop each component.
echo   Or run: stop.bat to kill all.
echo.
pause
goto :end

:end_error
echo.
echo   Fix prerequisites above, then re-run.
pause
:end
endlocal
