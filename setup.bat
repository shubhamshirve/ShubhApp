@echo off
setlocal enabledelayedexpansion
title SaaS Billing Platform - Setup

echo.
echo  ==========================================
echo   SaaS Billing Platform - Local Setup
echo  ==========================================
echo.

REM  1. Check prerequisites
echo [1/7] Checking prerequisites...

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python 3.9+ is required but not found.
    echo          Download from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  [OK] Python !PY_VER! found.

node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js 16+ is required but not found.
    echo          Download from https://nodejs.org/
    pause
    exit /b 1
)
for /f %%v in ('node --version') do set NODE_VER=%%v
echo  [OK] Node.js !NODE_VER! found.

yarn --version >nul 2>&1
if errorlevel 1 (
    echo  [INFO] yarn not found, will use npm instead.
    set PKG_MGR=npm
    set PKG_INSTALL=npm install --force
) else (
    for /f %%v in ('yarn --version') do set YARN_VER=%%v
    echo  [OK] yarn !YARN_VER! found.
    set PKG_MGR=yarn
    set PKG_INSTALL=yarn install
)

mongod --version >nul 2>&1
if errorlevel 1 (
    echo  [WARN] MongoDB not found in PATH.
    echo         Make sure MongoDB is installed and running on port 27017.
    echo         Download from https://www.mongodb.com/try/download/community
) else (
    echo  [OK] MongoDB found.
)

echo.

REM  2. Backend - Virtual Environment
echo [2/7] Setting up Python virtual environment...
cd /d "%~dp0backend"

if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created at backend\venv
) else (
    echo  [OK] Virtual environment already exists.
)

echo.

REM  3. Backend - Install Dependencies
echo [3/7] Installing backend Python dependencies...
call venv\Scripts\activate.bat

pip install --upgrade pip --quiet
pip install -r requirements_local.txt
if errorlevel 1 (
    echo  [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)
echo  [OK] Backend dependencies installed.
call venv\Scripts\deactivate.bat

echo.

REM  4. Shared Environment - Create root .env if not exists
echo [4/7] Configuring shared environment...
cd /d "%~dp0"
if not exist ".env" (
    (
        echo DOMAIN=localhost
        echo SERVER_IP=
        echo MONGO_URI=mongodb://mongodb:27017/saas_db
        echo MONGO_URL=mongodb://localhost:27017/saas_db
        echo DB_NAME=saas_db
        echo CORS_ORIGINS=http://localhost:3000,http://localhost:8001,https://localhost,http://localhost
        echo REACT_APP_BACKEND_URL=http://localhost:8001
        echo JWT_SECRET=change-this-to-a-strong-random-secret
        echo RAZORPAY_KEY_ID=your_razorpay_key_id
        echo RAZORPAY_KEY_SECRET=your_razorpay_key_secret
        echo WHATSAPP_PHONE_NUMBER_ID=
        echo WHATSAPP_ACCESS_TOKEN=
        echo WHATSAPP_BUSINESS_ACCOUNT_ID=
        echo BACKUP_PASSWORD=change-this-backup-password
    ) > .env
    echo  [CREATED] .env with shared backend, frontend, and Docker settings.
) else (
    echo  [OK] root .env already exists.
)

echo.

REM  5. Frontend - Install Dependencies
echo [5/7] Installing frontend dependencies...
cd /d "%~dp0frontend"

if not exist "node_modules" (
    call %PKG_INSTALL%
    if errorlevel 1 (
        echo  [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
    echo  [OK] Frontend dependencies installed.
) else (
    echo  [OK] node_modules already exists. Skipping install.
    echo       Run "%PKG_MGR% install" manually if you need to update packages.
)

echo.

REM  6. Frontend - Shared env is already available from root .env
echo [6/7] Configuring frontend environment...
echo  [OK] Frontend reads REACT_APP_BACKEND_URL from the root .env file.

cd /d "%~dp0"
echo.

REM  7. Finalize
echo [7/7] Finalizing setup...
echo  [OK] Shared environment is configured in the root .env file.

echo.
echo  ==========================================
echo   Setup Complete!
echo  ==========================================
echo.
echo   Next steps:
echo   1. Make sure MongoDB is running on port 27017
echo   2. Update the root .env with your real credentials
echo   3. Run RunApp.bat to start the application
echo   4. Open http://localhost:3000 in your browser
echo.
echo   Default admin login:
echo     Email   : admin@saas.com
echo     Password: admin123
echo.
pause
