@echo off
echo ========================================
echo PM - AI-Assisted Demo - Stopping Local Services
echo ========================================
echo.

echo Stopping Backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

echo Stopping Frontend (port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

echo.
echo ========================================
echo Services Stopped
echo ========================================
echo.
pause
