# Local Installation Guide (Without Docker)

This guide will help you run the PM - AI-Assisted Demo application locally on your machine without Docker.

## Prerequisites

### 1. Python 3.11+

**Check if installed:**
```bash
python --version
```

**If not installed:**
- Download from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"
- Verify: `python --version` should show 3.11 or higher

### 2. Node.js 18+

**Check if installed:**
```bash
node --version
npm --version
```

**If not installed:**
- Download from [nodejs.org](https://nodejs.org/)
- Install LTS version (18.x or higher)
- Verify: `node --version` should show v18 or higher

### 3. Microsoft ODBC Driver 18 for SQL Server

**Windows:**

Download and install from: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

Or use PowerShell:
```powershell
# Download installer
Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/?linkid=2249004" -OutFile "msodbcsql.msi"

# Install
msiexec /i msodbcsql.msi /qn IACCEPTMSODBCSQLLICENSETERMS=YES
```

**Verify installation:**
```bash
# Check installed ODBC drivers
odbcad32
```
You should see "ODBC Driver 18 for SQL Server" in the list.

### 4. SQL Server Access

Ensure you have:
- SQL Server instance accessible from your machine
- Database `dyson_pm` created
- Credentials with CREATE TABLE permissions

## Backend Setup

### Step 1: Navigate to Backend Directory

```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\backend
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (Command Prompt):
venv\Scripts\activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# If you get execution policy error in PowerShell:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

You should see `(venv)` prefix in your terminal.

### Step 3: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI
- Uvicorn
- SQLAlchemy
- pyodbc
- OpenAI
- Anthropic
- Google Generative AI
- And other dependencies

**If you get errors:**

```bash
# Try installing one by one to identify the problematic package
pip install fastapi
pip install uvicorn[standard]
pip install sqlalchemy
pip install pyodbc
pip install openai
pip install anthropic
pip install google-generativeai
pip install pydantic
pip install pydantic-settings
pip install python-dotenv
```

### Step 5: Configure Environment Variables

Create `.env` file in the `backend` directory:

```bash
# Copy from example
copy .env.example .env

# Or create manually
notepad .env
```

Edit `.env` with your configuration:

```env
# Application Settings
APP_NAME=AI-Assisted Preventive Maintenance POC
APP_VERSION=1.0.0
DEBUG=True

# Database Configuration (External MS SQL Server)
# IMPORTANT: Replace YOUR_SQL_SERVER_HOST with your actual SQL Server
# Examples:
#   localhost:1433
#   192.168.1.100:1433
#   sqlserver.company.local:1433
#   yourserver.database.windows.net:1433 (Azure SQL)
DATABASE_URL=mssql+pyodbc://sa:YourPassword@localhost:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# LLM Provider Configuration
LLM_PROVIDER=openai

# API Keys (add at least one)
OPENAI_API_KEY=sk-proj-your-actual-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here
GOOGLE_API_KEY=your-actual-google-key-here

# AI Decision Confidence Threshold
CONFIDENCE_THRESHOLD=0.7

# SMTP Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=True

# PM Detection Window
PM_DUE_DAYS=30

# CORS Origins
CORS_ORIGINS=http://localhost:3000

# API Version Prefix
API_V1_PREFIX=/api/v1
```

**Important:** Update these values:
- `DATABASE_URL` - Replace with your SQL Server connection string
- `OPENAI_API_KEY` - Add your actual API key (or use Claude/Gemini)

### Step 6: Test Database Connection

```bash
python -c "from app.database import engine; conn = engine.connect(); print('✓ Database connection successful!'); conn.close()"
```

If successful, you'll see: `✓ Database connection successful!`

**If connection fails:**
- Verify SQL Server is running
- Check hostname/IP in DATABASE_URL
- Verify credentials are correct
- Ensure SQL Server allows TCP/IP connections
- Check firewall allows port 1433

### Step 7: Initialize Database

```bash
# Create tables
python -m app.scripts.init_db

# Generate test data (75 machines)
python -m app.scripts.seed_data
```

Expected output:
```
Database initialized successfully.
Tables created: machines, maintenance_history, work_orders, ai_decisions, workflow_logs

Generating 75 test machines...
✓ Created 15 overdue machines
✓ Created 25 due soon machines
✓ Created 35 OK machines
✓ Generated maintenance history
Database seeded successfully with 75 machines!
```

### Step 8: Run Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or without reload
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test backend is running:**
- Open browser: http://localhost:8000
- API docs: http://localhost:8000/docs

**Keep this terminal running!** Open a new terminal for frontend setup.

## Frontend Setup

### Step 1: Open New Terminal

Keep the backend terminal running and open a new terminal window.

### Step 2: Navigate to Frontend Directory

```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\frontend
```

### Step 3: Install Dependencies

```bash
npm install
```

This will install:
- React 18
- Material-UI
- React Router
- Axios
- Date-fns
- And other dependencies

**If you get errors:**

```bash
# Clear npm cache and try again
npm cache clean --force
npm install

# Or delete node_modules and reinstall
rmdir /s /q node_modules
del package-lock.json
npm install
```

### Step 4: Configure Environment

Create `.env` file in the `frontend` directory:

```bash
# Create .env file
notepad .env
```

Add this content:

```env
# Backend API URL
REACT_APP_API_URL=http://localhost:8000/api/v1

# Optional: Browser auto-open
BROWSER=none
```

### Step 5: Run Frontend Development Server

```bash
npm start
```

You should see:
```
Compiled successfully!

You can now view frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.1.x:3000

Note that the development build is not optimized.
To create a production build, use npm run build.

webpack compiled successfully
```

**The browser should automatically open http://localhost:3000**

If not, manually open: http://localhost:3000

## Verify Everything Works

### 1. Check Backend API

Open: http://localhost:8000/docs

You should see Swagger UI with all API endpoints.

### 2. Test API Endpoint

```bash
# Get all machines
curl http://localhost:8000/api/v1/machines

# Or open in browser:
# http://localhost:8000/api/v1/machines
```

### 3. Check Frontend

Open: http://localhost:3000

You should see:
- Machine Dashboard with 75 machines
- Summary cards showing:
  - 15 Overdue (Red)
  - 25 Due Soon (Yellow)
  - 35 OK (Green)
  - 75 Total

### 4. Test AI Decision

1. Click on any machine card
2. Click "Get AI Decision" button
3. You should see AI decision with:
   - Decision (CREATE_WORK_ORDER, SEND_NOTIFICATION, or WAIT)
   - Priority (Low, Medium, High)
   - Confidence (0.0 to 1.0)
   - Explanation

### 5. Test Work Order Approval

1. Navigate to "Work Orders" tab
2. Filter by "Pending Approval"
3. Click green checkmark icon
4. Enter approver name
5. Click "Approve"

## Running Both Services

You need **two terminals** running simultaneously:

**Terminal 1 (Backend):**
```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\frontend
npm start
```

## Stopping Services

**Stop Backend:**
- Press `CTRL+C` in the backend terminal

**Stop Frontend:**
- Press `CTRL+C` in the frontend terminal

## Running n8n Workflow (Optional)

If you want to run the automated daily PM checker workflow:

### Option 1: Using Docker (n8n only)

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v E:\RepoInno\Dyson_WODemo\Dyson_Workflow\workflows:/home/node/.n8n/workflows \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=admin123 \
  n8nio/n8n
```

Access: http://localhost:5678 (admin / admin123)

### Option 2: Install n8n Locally

```bash
# Install n8n globally
npm install -g n8n

# Run n8n
n8n start

# Access: http://localhost:5678
```

## Troubleshooting

### Backend Issues

#### Import Error: No module named 'app'

**Problem:** Python can't find the app module

**Solution:**
```bash
# Make sure you're in the backend directory
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\backend

# Make sure virtual environment is activated
venv\Scripts\activate

# Run from backend directory
uvicorn app.main:app --reload
```

#### Database Connection Error

**Problem:** Can't connect to SQL Server

**Solutions:**

1. **Test connection manually:**
   ```bash
   python -c "from app.database import engine; print(engine.connect())"
   ```

2. **Check SQL Server is running:**
   ```bash
   # Windows Services
   services.msc
   # Look for "SQL Server (MSSQLSERVER)" or your instance name
   ```

3. **Verify connection string:**
   ```env
   # In .env file, try different formats:

   # Format 1: localhost
   DATABASE_URL=mssql+pyodbc://sa:Password@localhost:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

   # Format 2: 127.0.0.1
   DATABASE_URL=mssql+pyodbc://sa:Password@127.0.0.1:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

   # Format 3: computer name
   DATABASE_URL=mssql+pyodbc://sa:Password@DESKTOP-ABC123:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
   ```

4. **Enable TCP/IP in SQL Server:**
   - Open "SQL Server Configuration Manager"
   - Navigate to "SQL Server Network Configuration" → "Protocols for [Instance]"
   - Enable "TCP/IP"
   - Restart SQL Server service

#### ODBC Driver Not Found

**Error:** `[Microsoft][ODBC Driver Manager] Data source name not found`

**Solution:**
1. Download ODBC Driver 18: https://go.microsoft.com/fwlink/?linkid=2249004
2. Install it
3. Verify in Control Panel → Administrative Tools → ODBC Data Sources

#### LLM API Key Error

**Error:** `AuthenticationError` or `InvalidAPIKey`

**Solution:**
```env
# In .env file, make sure API key is correct and active

# For OpenAI - should start with sk-proj- or sk-
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# For Anthropic - should start with sk-ant-
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# For Google - no specific prefix
GOOGLE_API_KEY=xxxxxxxxxxxxx
```

### Frontend Issues

#### Port 3000 Already in Use

**Error:** `Something is already running on port 3000`

**Solution:**

```bash
# Option 1: Kill the process using port 3000
# Find process
netstat -ano | findstr :3000

# Kill process (replace PID)
taskkill /PID <PID> /F

# Option 2: Use different port
# In frontend directory, create .env file:
PORT=3001
npm start
```

#### Blank Page or Loading Forever

**Problem:** Frontend loads but shows blank page

**Solutions:**

1. **Check console for errors:**
   - Press F12 in browser
   - Look at Console tab for errors

2. **Verify backend is running:**
   - Open http://localhost:8000/docs
   - Should show API documentation

3. **Check CORS settings:**
   - In backend `.env`, make sure:
     ```env
     CORS_ORIGINS=http://localhost:3000
     ```

4. **Clear browser cache:**
   - Press CTRL+SHIFT+DELETE
   - Clear cached images and files
   - Refresh page

#### npm install Errors

**Error:** Various npm installation errors

**Solutions:**

```bash
# Solution 1: Clear cache
npm cache clean --force
npm install

# Solution 2: Delete node_modules
rmdir /s /q node_modules
del package-lock.json
npm install

# Solution 3: Use different registry
npm config set registry https://registry.npmjs.org/
npm install

# Solution 4: Install with legacy peer deps
npm install --legacy-peer-deps
```

#### API Request Failed

**Error:** Network Error or Failed to fetch

**Solutions:**

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/api/v1/machines
   ```

2. **Verify API URL in frontend .env:**
   ```env
   REACT_APP_API_URL=http://localhost:8000/api/v1
   ```

3. **Restart frontend:**
   ```bash
   # Stop with CTRL+C
   npm start
   ```

## Development Tips

### Auto-reload on Code Changes

**Backend:** Already enabled with `--reload` flag
- Edit any Python file in `app/`
- Server automatically restarts

**Frontend:** Already enabled by default
- Edit any file in `src/`
- Browser automatically refreshes

### View Logs

**Backend logs:**
- Displayed in the terminal running uvicorn
- Or add logging:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.info("Your message here")
  ```

**Frontend logs:**
- Browser console (F12 → Console)
- Or add console.log:
  ```javascript
  console.log("Your message here");
  ```

### Database Management

**View data in SQL Server:**

```sql
-- Connect to SQL Server
USE dyson_pm;

-- View all machines
SELECT * FROM machines;

-- View work orders
SELECT * FROM work_orders;

-- View AI decisions
SELECT * FROM ai_decisions;

-- View maintenance history
SELECT * FROM maintenance_history;
```

**Reset database:**

```bash
# Drop all data
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\backend
venv\Scripts\activate

# Re-initialize
python -m app.scripts.init_db
python -m app.scripts.seed_data
```

## Production Build

### Backend (Production)

```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\backend
venv\Scripts\activate

# Run with production settings
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend (Production)

```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp\frontend

# Build production bundle
npm run build

# Serve with a static server
npm install -g serve
serve -s build -l 3000
```

## Quick Start Script

Create `start_local.bat` in `Dyson_WOApp` directory:

```batch
@echo off
echo Starting PM - AI-Assisted Demo Application Locally...
echo.

echo Starting Backend...
start cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 5

echo Starting Frontend...
start cmd /k "cd frontend && npm start"

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit...
pause
```

**Usage:**
```bash
# Double-click start_local.bat
# Or run from command line:
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp
start_local.bat
```

## Summary of URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | None |
| Backend API | http://localhost:8000 | None |
| API Documentation | http://localhost:8000/docs | None |
| n8n (if running) | http://localhost:5678 | admin / admin123 |

## Next Steps

1. ✅ Backend running on port 8000
2. ✅ Frontend running on port 3000
3. ✅ Database initialized with 75 test machines
4. 📖 Read [README.md](../README.md) for usage guide
5. 📖 Read [EXTERNAL_SQL_SETUP.md](EXTERNAL_SQL_SETUP.md) for SQL Server setup
6. 🔧 Configure n8n workflow for automated PM checks (optional)

## Getting Help

If you encounter issues:

1. Check logs in both terminal windows
2. Review troubleshooting section above
3. Check [README.md](../README.md) for general documentation
4. Review [EXTERNAL_SQL_SETUP.md](EXTERNAL_SQL_SETUP.md) for database issues
