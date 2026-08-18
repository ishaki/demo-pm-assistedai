@echo off
echo ========================================
echo PM - AI-Assisted Demo - Local Development Startup
echo ========================================
echo.

echo [1/2] Starting Backend API...
start "PM - AI-Assisted Demo - Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo [2/2] Starting Frontend...
start "PM - AI-Assisted Demo - Frontend" cmd /k "cd frontend && npm start"

echo.
echo ========================================
echo Services Starting...
echo ========================================
echo.
echo Backend API:      http://localhost:8000
echo API Docs:         http://localhost:8000/docs
echo Frontend UI:      http://localhost:3000
echo.
echo Press any key to close this window...
echo (Backend and Frontend will continue running)
echo ========================================
pause >nul
