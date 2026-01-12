@echo off
REM Start script for LLM Council on Windows

echo Starting LLM Council...

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: uv is not installed. Please install it from: https://docs.astral.sh/uv/
    exit /b 1
)

REM Check if npm is installed
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: npm is not installed. Please install Node.js and npm
    exit /b 1
)

echo Starting backend server...
start "LLM Council Backend" cmd /k "uv run python -m backend.main"

timeout /t 3 /nobreak >nul

echo Starting frontend development server...
cd frontend
start "LLM Council Frontend" cmd /k "npm run dev"
cd ..

echo.
echo LLM Council is running!
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5173
echo.
echo Close the terminal windows to stop the servers
