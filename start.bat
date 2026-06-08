@echo off
<<<<<<< HEAD
chcp 936 >nul 2>&1
setlocal enabledelayedexpansion

set "BASE_DIR=%~dp0"
:: Remove trailing backslash to avoid quote escaping issues
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
set "BACKEND_DIR=%BASE_DIR%\backend"
set "AI_DIR=%BASE_DIR%\ai-models"
set "MODEL_DIR=%BASE_DIR%\models"
set "DATA_DIR=%BACKEND_DIR%\data"
set "CONDA_ENV=%BASE_DIR%\.conda\yolov8-security"

echo.
echo  ===========================================
echo    YOLOv8 Security System - One Click Start
echo  ===========================================
echo.

:: ==========================================
:: 1. Check prerequisites
:: ==========================================
echo [1/6] Checking environment...

:: Java - try bundled JDK first (system java may be broken)
set "JAVA_CMD="

:: Try direct known JDK path first (fastest)
if exist "%BASE_DIR%\jdk-18.0.2.1+1\bin\java.exe" (
    set "JAVA_CMD=%BASE_DIR%\jdk-18.0.2.1+1\bin\java.exe"
    echo    Java: bundled JDK OK
    goto :check_conda
)

:: Scan for any jdk* directory with java.exe
for /f "delims=" %%i in ('dir /b /ad "%BASE_DIR%" 2^>nul ^| findstr /i "^jdk"') do (
    if exist "%BASE_DIR%%%i\bin\java.exe" (
        set "JAVA_CMD=%BASE_DIR%\%%i\bin\java.exe"
        echo    Java: bundled JDK OK
        goto :check_conda
    )
)

:: Fallback to system java
where java >nul 2>&1
if %errorlevel% equ 0 (
    java -version >nul 2>&1
    if !errorlevel! equ 0 (
        set "JAVA_CMD=java"
        echo    Java: system java OK
        goto :check_conda
    )
)

echo [ERROR] Java not found!
echo    Install JDK 18 or ensure jdk-18 folder exists in project root.
pause
exit /b 1

:check_conda
:: Conda env
if not exist "%CONDA_ENV%\python.exe" (
    echo [ERROR] Conda env not found: %CONDA_ENV%
    echo    Run: conda create -p "%CONDA_ENV%" python=3.10
    pause
    exit /b 1
=======
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
echo   [1/4] Java...
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
echo   [2/4] Python...
set PYTHON_OK=0
if exist "%PROJECT_ROOT%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"
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
echo   [3/4] Maven...
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
echo   [4/4] Node...
set NODE_OK=0
where node >nul 2>&1 && set NODE_OK=1
if !NODE_OK!==0 (
    echo   [WARN] Node not found - frontend dev server will be skipped
    set SKIP_FRONTEND=1
) else (
    for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
    echo   [OK]   Node: !NODE_VER!
)

:: --- Port check (single netstat call) ---
echo.
echo   Checking ports...
set PORT_CONFLICT=0
for /f "tokens=*" %%L in ('netstat -ano 2^>nul ^| findstr "LISTENING"') do (
    echo %%L | findstr ":5000 :5001 :5173" >nul 2>&1
    if !errorlevel!==0 (
        set /a PORT_CONFLICT+=1
    )
)
if !PORT_CONFLICT! gtr 0 (
    echo   [WARN] !PORT_CONFLICT! ports (5000/5001/5173) already in use
    choice /C YN /M "   Continue anyway?"
    if errorlevel 2 goto :end
>>>>>>> cursor/fix-workspace-nav-router
)
echo    Python: conda env OK

<<<<<<< HEAD
:: Model
if not exist "%MODEL_DIR%\yolov8n-pose.pt" (
    echo [ERROR] Model not found: models\yolov8n-pose.pt
    pause
    exit /b 1
)
echo    Model: OK

:: ==========================================
:: 2. Auto-create .env if missing
:: ==========================================
echo.
echo [2/6] Checking config...
if not exist "%BASE_DIR%\.env" (
    if exist "%BASE_DIR%\.env.example" (
        copy "%BASE_DIR%\.env.example" "%BASE_DIR%\.env" >nul
        echo    Created .env from .env.example
    ) else (
        echo API_KEY=default-dev-token> "%BASE_DIR%\.env"
        echo    Created .env with default token
    )
) else (
    echo    .env: OK
)

:: ==========================================
:: 3. Ensure data directory exists
:: ==========================================
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

:: ==========================================
:: 4. Build WAR (always rebuild to pick up template changes)
:: ==========================================
echo.
echo [3/6] Building backend with Maven...
set "MAVEN_JAR=%BASE_DIR%\.mvn\wrapper\maven-wrapper.jar"
if not exist "%MAVEN_JAR%" set "MAVEN_JAR=%BASE_DIR%\maven-wrapper\maven-wrapper.jar"
"%JAVA_CMD%" "-Dmaven.multiModuleProjectDirectory=%BASE_DIR%" -classpath "%MAVEN_JAR%" org.apache.maven.wrapper.MavenWrapperMain -f backend\pom.xml clean package -DskipTests
if %errorlevel% neq 0 (
    echo [ERROR] Maven build failed!
    pause
    exit /b 1
)
echo    Build complete.

:: ==========================================
:: 5. Start Spring Boot backend
:: ==========================================
:start_backend
echo.
echo [4/6] Starting Spring Boot backend (port 5000)...
set "WAR_PATH=%BACKEND_DIR%\target\yolov8-security.war"
start "YOLOv8-Backend" "%JAVA_CMD%" -jar "%WAR_PATH%"

:: ==========================================
:: 6. Wait for backend ready
:: ==========================================
echo.
echo [5/6] Waiting for backend...
set RETRY=0

:wait_loop
timeout /t 2 /nobreak >nul
set /a RETRY+=1
if !RETRY! gtr 30 (
    echo    Backend taking too long, continuing...
    goto :start_python
)
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:5000/yolov8-security/ 2>nul | findstr "200 302" >nul
if !errorlevel! neq 0 (
    echo    Waiting... [!RETRY!/30]
    goto :wait_loop
)
echo    Backend ready!

:: ==========================================
:: 7. Start Python detection
:: ==========================================
:start_python
echo.
echo [6/6] Starting Python AI detection...
set "PY_EXE=%CONDA_ENV%\python.exe"
start "YOLOv8-Detection" cmd /k "cd /d "%AI_DIR%" && "%PY_EXE%" yolov8_security.py"

:: ==========================================
:: Done
:: ==========================================
echo.
echo  ===========================================
echo    All services started!
echo.
echo    Backend:   http://127.0.0.1:5000/yolov8-security
echo    Detection: running in separate window
echo  ===========================================
echo.
echo    Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000/yolov8-security"

echo.
echo    Close this window to stop monitoring.
pause >nul
=======
:: ============================================================
::   Build
:: ============================================================
echo.
echo %SEP%
echo   Build
echo %SEP%

set "WAR_FILE=%PROJECT_ROOT%server\target\yolov8-security.war"

if !SKIP_BUILD!==1 (
    if exist "!WAR_FILE!" (
        echo   [SKIP] Build (--no-build, WAR exists)
        goto :start_components
    )
    echo   [WARN] --no-build but WAR missing, building anyway...
)

:: Clean stale .original file (Windows rename issue)
if exist "!WAR_FILE!.original" del /f "!WAR_FILE!.original" >nul 2>&1

if exist "!WAR_FILE!" (
    echo   [BUILD] Maven package (incremental, skip clean)...
    pushd "%PROJECT_ROOT%server"
    call !MVN_CMD! package -DskipTests -q
    if !errorlevel! neq 0 (
        echo   [WARN] Incremental build failed, retrying with clean...
        call !MVN_CMD! clean package -DskipTests -q
    )
) else (
    echo   [BUILD] Maven clean package (first build)...
    pushd "%PROJECT_ROOT%server"
    call !MVN_CMD! clean package -DskipTests -q
)
if !errorlevel! neq 0 (
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

set "JAVA_OPTS=-Xmx512m"

:: --- Python Detection ---
if !SKIP_PYTHON!==1 (
    echo   [SKIP] Python detection module
    goto :start_backend_5000
)
echo   [START] Python detection module...
start "Detection" cmd /k "cd /d "%PROJECT_ROOT%detection" && "!PYTHON_EXE!" yolov8_security.py"
echo   [OK]   Detection started in new window

:: --- Java Backend :5000 ---
:start_backend_5000
echo   [START] Java backend (port 5000, live data)...
start "Backend-5000" cmd /k "cd /d "%PROJECT_ROOT%server" && "!JAVA_EXE!" !JAVA_OPTS! -jar target\yolov8-security.war --server.port=5000"
echo   [OK]   Backend started in new window

:: --- Java Backend :5001 ---
if !SKIP_EMPTY!==1 (
    echo   [SKIP] Empty-data backend
    goto :start_frontend
)
echo   [START] Java backend (port 5001, empty data)...
start "Backend-5001" cmd /k "cd /d "%PROJECT_ROOT%server" && "!JAVA_EXE!" !JAVA_OPTS! -DDATA_DIR=./data_empty -jar target\yolov8-security.war --server.port=5001"
echo   [OK]   Empty-data backend started in new window

:: --- Frontend ---
:start_frontend
if !SKIP_FRONTEND!==1 (
    echo   [SKIP] Frontend dev server
    goto :done
)
if !PROD_MODE!==1 (
    echo   [INFO]  Production mode - frontend served by Java at port 5000
    echo   [INFO]  Run build.bat first if you haven't built yet
    goto :done
)

echo   [START] Frontend dev server (port 5173)...
if not exist "%PROJECT_ROOT%web\node_modules" (
    echo   [INFO]  node_modules not found, running npm install first...
    pushd "%PROJECT_ROOT%web" && call npm install && popd
)
start "Frontend-5173" cmd /k "cd /d "%PROJECT_ROOT%web" && npm run dev"

:done
echo.
echo %SEP%
echo   All Components Started
echo %SEP%
echo.
echo     Detection  :  Python window (if not skipped)
echo     Backend    :  http://localhost:5000 (live data)
echo     Backend    :  http://localhost:5001 (empty data, if not skipped)
if !SKIP_FRONTEND!==0 if !PROD_MODE!==0 (
    echo     Frontend   :  http://localhost:5173
)
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
>>>>>>> cursor/fix-workspace-nav-router
endlocal
