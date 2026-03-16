@echo off
setlocal enabledelayedexpansion
title SaaS Billing Platform - Setup

echo.
echo  ==========================================
echo   SaaS Billing Platform - Local Setup
echo  ==========================================
echo.

REM ──────────────────────────────────────────
REM  1. Check Prerequisites
REM ──────────────────────────────────────────
echo [1/6] Checking prerequisites...

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

REM Check yarn, fallback to npm
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

REM Check MongoDB
mongod --version >nul 2>&1
if errorlevel 1 (
    echo  [WARN] MongoDB not found in PATH.
    echo         Make sure MongoDB is installed and running on port 27017.
    echo         Download from https://www.mongodb.com/try/download/community
) else (
    for /f "tokens=3" %%v in ('mongod --version 2^>^&1 ^| findstr "db version"') do set MONGO_VER=%%v
    echo  [OK] MongoDB found.
)

echo.

REM ──────────────────────────────────────────
REM  2. Backend - Virtual Environment
REM ──────────────────────────────────────────
echo [2/6] Setting up Python virtual environment...
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

REM ──────────────────────────────────────────
REM  3. Backend - Install Dependencies
REM ──────────────────────────────────────────
echo [3/6] Installing backend Python dependencies...
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

REM ──────────────────────────────────────────
REM  4. Backend - Create .env if not exists
REM ──────────────────────────────────────────
echo [4/6] Configuring backend environment...
if not exist ".env" (
    (
        echo MONGO_URL=mongodb://localhost:27017
        echo DB_NAME=saas_billing_db
        echo CORS_ORIGINS=http://localhost:3000
        echo JWT_SECRET=change-this-to-a-strong-random-secret
        echo RAZORPAY_KEY_ID=your_razorpay_key_id
        echo RAZORPAY_KEY_SECRET=your_razorpay_key_secret
        echo WHATSAPP_PHONE_NUMBER_ID=
        echo WHATSAPP_ACCESS_TOKEN=
        echo WHATSAPP_BUSINESS_ACCOUNT_ID=
    ) > .env
    echo  [CREATED] backend\.env — please update with your credentials.
) else (
    echo  [OK] backend\.env already exists.
)

cd /d "%~dp0"
echo.

REM ──────────────────────────────────────────
REM  5. Frontend - Install Dependencies
REM ──────────────────────────────────────────
echo [5/6] Installing frontend dependencies...
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

REM ──────────────────────────────────────────
REM  6. Frontend - Create .env.local for local backend
REM ──────────────────────────────────────────
echo [6/6] Configuring frontend environment...
if not exist ".env.local" (
    (
        echo REACT_APP_BACKEND_URL=http://localhost:8001
    ) > .env.local
    echo  [CREATED] frontend\.env.local with REACT_APP_BACKEND_URL=http://localhost:8001
) else (
    echo  [OK] frontend\.env.local already exists.
)

cd /d "%~dp0"
echo.
echo  ==========================================
echo   Setup Complete!
echo  ==========================================
echo.
echo   Next steps:
echo   1. Make sure MongoDB is running on port 27017
echo   2. Update backend\.env with your Razorpay credentials
echo   3. Run RunApp.bat to start the application
echo   4. Open http://localhost:3000 in your browser
echo.
echo   Default admin login:
echo     Email   : admin@saas.com
echo     Password: admin123
echo.
pause
