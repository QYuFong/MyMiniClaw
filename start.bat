@echo off
echo ========================================
echo Mini-OpenClaw Startup Script
echo ========================================
echo.

REM Check Conda
where conda >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Conda not found. Please install Anaconda or Miniconda
    pause
    exit /b 1
)

REM Find conda installation path
for /f "delims=" %%i in ('where conda') do set CONDA_EXE=%%i
for %%i in ("%CONDA_EXE%") do set CONDA_DIR=%%~dpi
set CONDA_ROOT=%CONDA_DIR%..
set CONDA_ACTIVATE=%CONDA_ROOT%\Scripts\activate.bat

REM Check if activate.bat exists
if not exist "%CONDA_ACTIVATE%" (
    echo [ERROR] Conda activate script not found at: %CONDA_ACTIVATE%
    echo Please check your Anaconda/Miniconda installation
    pause
    exit /b 1
)

REM Check if miniclaw environment exists
call conda env list | findstr "miniclaw" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Conda environment 'miniclaw' not found.
    echo Please create it first: conda create -n miniclaw python=3.12
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/4] Activating miniclaw environment...
call "%CONDA_ACTIVATE%" miniclaw
if errorlevel 1 (
    echo [ERROR] Failed to activate miniclaw environment
    pause
    exit /b 1
)
echo Conda environment 'miniclaw' activated successfully

echo [2/4] Checking backend environment...
cd backend
if not exist .env (
    echo [WARNING] .env file not found. Please configure environment variables first.
    echo Run: copy .env.example .env
    echo Then edit .env file to add your API Keys
    call conda deactivate
    pause
    exit /b 1
)

echo [3/4] Installing backend dependencies in miniclaw environment...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing backend dependencies...
    pip install -r requirements.txt
) else (
    echo Backend dependencies already installed
)

echo [4/4] Installing frontend dependencies...
cd ..\frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
) else (
    echo Frontend dependencies already installed
)

echo.
echo ========================================
echo Starting services...
echo Backend will start on port 8002 (miniclaw env)
echo Frontend will start on port 3000
echo ========================================
echo.

REM Start backend in new window with conda environment
cd ..\backend
start "Mini-OpenClaw Backend" cmd /k ""%CONDA_ACTIVATE%" miniclaw && python -m uvicorn app:app --port 8002 --host 0.0.0.0 --reload"

REM Wait 2 seconds
timeout /t 2 /nobreak >nul

REM Start frontend in new window
cd ..\frontend
start "Mini-OpenClaw Frontend" cmd /k "npm run dev"

REM Deactivate conda environment in current window (if deactivate.bat exists)
if exist "%CONDA_ROOT%\Scripts\deactivate.bat" (
    call "%CONDA_ROOT%\Scripts\deactivate.bat"
)

echo.
echo ========================================
echo Startup complete!
echo.
echo Local access: http://localhost:3000
echo LAN access: http://YOUR_IP:3000
echo.
echo Note: Backend is running in 'miniclaw' conda environment
echo Press any key to close this window...
echo ========================================
pause >nul
