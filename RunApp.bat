@echo off
setlocal enabledelayedexpansion
title SaaS Billing Platform - Launcher

echo.
echo  ==========================================
echo   SaaS Billing Platform - Starting App
echo  ==========================================
echo.

REM ──────────────────────────────────────────
REM  Validate setup
REM ──────────────────────────────────────────
if not exist "%~dp0backend\venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo          Please run setup.bat first.
    pause
    exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
    echo  [ERROR] Frontend node_modules not found.
    echo          Please run setup.bat first.
    pause
    exit /b 1
)

REM ──────────────────────────────────────────
REM  Check MongoDB
REM ──────────────────────────────────────────
echo  Checking MongoDB connection...
"%~dp0backend\venv\Scripts\python.exe" -c "import pymongo; pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000).server_info(); print('OK')" >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Cannot connect to MongoDB on localhost:27017
    echo         Make sure MongoDB is running before proceeding.
    echo.
    choice /c YN /m "Continue anyway?"
    if errorlevel 2 exit /b 1
) else (
    echo  [OK] MongoDB is reachable.
)

echo.

REM ──────────────────────────────────────────
REM  Start Backend (FastAPI)
REM ──────────────────────────────────────────
echo  Starting Backend on http://localhost:8000 ...
start "SaaS Backend" cmd /k ^"cd /d "%~dp0backend" ^& call venv\Scripts\activate.bat ^& echo Backend starting... ^& uvicorn server:app --host 0.0.0.0 --port 8000 --reload^"

REM Give backend a moment to start
timeout /t 3 /nobreak >nul

REM ──────────────────────────────────────────
REM  Start Frontend (React)
REM ──────────────────────────────────────────
echo  Starting Frontend on http://localhost:3000 ...

REM Determine package manager
yarn --version >nul 2>&1
if errorlevel 1 (
    set START_CMD=npm start
) else (
    set START_CMD=yarn start
)

start "SaaS Frontend" cmd /k ^"cd /d "%~dp0frontend" ^& echo Frontend starting... ^& %START_CMD%^"

REM ──────────────────────────────────────────
REM  Open browser after a short delay
REM ──────────────────────────────────────────
echo.
echo  Waiting for services to start...
timeout /t 8 /nobreak >nul

echo  Opening browser...
start "" "http://localhost:3000"

echo.
echo  ==========================================
echo   App is running!
echo  ==========================================
echo.
echo   Frontend  : http://localhost:3000
echo   Backend   : http://localhost:8000
echo   API Docs  : http://localhost:8000/docs
echo.
echo   Admin Login:
echo     Email   : admin@saas.com
echo     Password: admin123
echo.
echo   Close the Backend and Frontend windows to stop the app.
echo.
pause
