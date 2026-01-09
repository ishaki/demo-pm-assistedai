@echo off
echo ========================================
echo PM - AI-Assisted Demo - Local Setup Script
echo ========================================
echo.

echo This script will help you set up the local development environment.
echo.
echo Prerequisites:
echo  - Python 3.12+ installed
echo  - Node.js 18+ installed
echo  - ODBC Driver 18 for SQL Server installed
echo  - SQL Server accessible with 'dyson_pm' database created
echo.
pause

echo.
echo ========================================
echo [1/6] Setting up Backend...
echo ========================================
cd backend

echo Checking Python version...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.12+
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
if not exist venv (
    py -3.12 -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo Creating .env file...
if not exist .env (
    copy .env.example .env
    echo .env file created from template.
    echo.
    echo IMPORTANT: Edit backend\.env file with your configuration:
    echo  - Update DATABASE_URL with your SQL Server connection
    echo  - Add at least one LLM API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)
    echo.
    echo Press any key when you've updated the .env file...
    pause >nul
) else (
    echo .env file already exists.
)

echo.
echo Testing database connection...
python -c "from app.database import engine; conn = engine.connect(); print('✓ Database connection successful!'); conn.close()"
if errorlevel 1 (
    echo.
    echo ERROR: Database connection failed!
    echo Please check your DATABASE_URL in backend\.env file.
    echo.
    pause
    exit /b 1
)

echo.
echo Initializing database...
python -m app.scripts.init_db
if errorlevel 1 (
    echo ERROR: Database initialization failed!
    pause
    exit /b 1
)

echo.
echo Generating test data (75 machines)...
python -m app.scripts.seed_data
if errorlevel 1 (
    echo ERROR: Seed data generation failed!
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo [2/6] Setting up Frontend...
echo ========================================
cd frontend

echo Checking Node.js version...
node --version
if errorlevel 1 (
    echo ERROR: Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo.
echo Installing npm dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install npm dependencies!
    pause
    exit /b 1
)

echo.
echo Creating frontend .env file...
if not exist .env (
    echo REACT_APP_API_URL=http://localhost:8000/api/v1 > .env
    echo BROWSER=none >> .env
    echo Frontend .env file created.
) else (
    echo Frontend .env file already exists.
)

cd ..

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo  1. Run 'start_local.bat' to start both backend and frontend
echo  2. Access frontend at http://localhost:3000
echo  3. Access API docs at http://localhost:8000/docs
echo.
echo Or start services manually:
echo.
echo Backend:
echo   cd backend
echo   venv\Scripts\activate
echo   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo Frontend:
echo   cd frontend
echo   npm start
echo.
echo ========================================
pause
