# AI-Assisted Preventive Maintenance POC

A comprehensive preventive maintenance management system leveraging AI/LLM capabilities to automate work order creation and maintenance scheduling decisions.

## Overview

This POC demonstrates an intelligent preventive maintenance system that uses AI to analyze machine PM schedules, maintenance history, and existing work orders to make informed decisions about maintenance actions. The system features a modern web interface, automated workflow execution, and multi-provider LLM support.

## Key Features

- **AI-Powered Decision Engine**: Configurable LLM provider (OpenAI GPT-4, Anthropic Claude, Google Gemini) for intelligent maintenance decisions
- **Automated Work Order Management**: AI-driven work order creation with confidence-based approval workflows
- **Machine Dashboard**: Real-time PM status monitoring with color-coded indicators (Red/Yellow/Green)
- **Multi-Status Tracking**: Track machines across overdue, due soon, and OK statuses
- **Email Notifications**: Automated supplier notifications for work orders and approvals
- **n8n Workflow Automation**: Daily scheduled checks for machines requiring PM
- **Audit Trail**: Complete logging of AI decisions and work order lifecycle
- **Docker Deployment**: One-command multi-container deployment

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: MS SQL Server 2022
- **ORM**: SQLAlchemy 2.x
- **LLM Integration**: OpenAI, Anthropic Claude, Google Gemini
- **Email**: SMTP with HTML templates

### Frontend
- **Framework**: React 18
- **UI Library**: Material-UI (MUI)
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Build Tool**: Create React App

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Workflow Automation**: n8n
- **Web Server**: Nginx (production)

## Architecture

```
Docker Environment                     External Services
┌──────────────────────────┐
│  ┌─────────────────┐     │          ┌────────────────┐
│  │   React UI      │:3000│          │   MS SQL       │
│  │  (Frontend)     │     │          │   Server       │
│  └────────┬────────┘     │          │  (External)    │
│           │              │          └────────▲───────┘
│           ↓              │                   │
│  ┌─────────────────┐     │                   │
│  │   FastAPI       │:8000├───────────────────┤
│  │   (Backend)     │     │                   │
│  └────────┬────────┘     │                   │
│           │              │          ┌────────┴───────┐
│           │              │          │  LLM Providers │
│           │              │          │ OpenAI/Claude/ │
│           ↓              │          │     Gemini     │
│  ┌─────────────────┐     │          └────────────────┘
│  │      n8n        │:5678│
│  │   Workflows     │     │          ┌────────────────┐
│  └─────────────────┘     │          │  SMTP Server   │
│                          │          │   (Optional)   │
└──────────────────────────┘          └────────────────┘
```

## Prerequisites

- **MS SQL Server** instance (local or remote)
  - SQL Server 2017 or later / Azure SQL Database
  - Database created: `dyson_pm`
  - Network access from Docker host
  - Credentials with CREATE TABLE permissions
- **Docker Desktop** 20.10+ (with Docker Compose)
- **API Keys** for at least one LLM provider:
  - OpenAI API Key (GPT-4 access)
  - OR Anthropic API Key (Claude access)
  - OR Google API Key (Gemini access)
- **SMTP Credentials** (optional, for email notifications)
- **System Requirements**: 4GB RAM, 10GB disk space

## Installation Options

Choose your preferred installation method:

### Option 1: Local Installation (Recommended for Development)

**Best for:** Local development, testing, or if you have Docker issues

📖 **[Follow the Local Installation Guide](Dyson_WOApp/LOCAL_INSTALLATION_GUIDE.md)** - Complete step-by-step instructions for running without Docker.

**Quick setup:**
```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp
setup_local.bat
```

**Start services:**
```bash
start_local.bat
```

### Option 2: Docker Installation

**Best for:** Production-like environment, easy deployment

Continue with the Quick Start guide below.

---

## Quick Start (Docker)

### 1. Prepare SQL Server Database

You need an external MS SQL Server instance. See **[EXTERNAL_SQL_SETUP.md](Dyson_WOApp/EXTERNAL_SQL_SETUP.md)** for detailed setup instructions.

**Quick Setup:**

**Option A: Using existing SQL Server instance**

Connect to your SQL Server and create the database:

```sql
-- Connect via SSMS, Azure Data Studio, or sqlcmd
CREATE DATABASE dyson_pm;
GO
```

**Option B: Using Azure SQL Database**

1. Create Azure SQL Database via Azure Portal
2. Database name: `dyson_pm`
3. Note the connection string
4. Update firewall rules to allow Docker host IP

> 📖 **Need help?** See the comprehensive [External SQL Server Setup Guide](Dyson_WOApp/EXTERNAL_SQL_SETUP.md) for:
> - Enabling TCP/IP and SQL Authentication
> - Firewall configuration
> - Connection string examples
> - Troubleshooting common issues

### 2. Clone and Navigate

```bash
cd E:\RepoInno\Dyson_WODemo
```

### 3. Configure Environment Variables

Create `.env` file in `Dyson_WOApp/backend/`:

```bash
cd Dyson_WOApp/backend
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database Configuration (External MS SQL Server)
# IMPORTANT: Replace YOUR_SQL_SERVER_HOST with your actual SQL Server hostname/IP
# Examples:
#   - IP address: 192.168.1.100
#   - Hostname: sqlserver.company.local
#   - Azure SQL: yourserver.database.windows.net
DATABASE_URL=mssql+pyodbc://sa:YourStrong!Passw0rd@YOUR_SQL_SERVER_HOST:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# LLM Provider Configuration (choose one)
LLM_PROVIDER=openai  # Options: openai, claude, gemini
CONFIDENCE_THRESHOLD=0.7

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4

# Anthropic Claude Configuration (if using Claude)
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Google Gemini Configuration (if using Gemini)
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_MODEL=gemini-1.5-pro

# SMTP Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=PM - AI-Assisted Demo System

# Application Settings
ENVIRONMENT=development
DEBUG=True
```

**Important Notes:**
- Replace `YOUR_SQL_SERVER_HOST` with your actual SQL Server hostname or IP address
- Update the username/password in `DATABASE_URL` to match your SQL Server credentials
- Add at least one LLM provider API key
- For Gmail SMTP, use an [App Password](https://support.google.com/accounts/answer/185833)
- Ensure SQL Server is accessible from Docker host (check firewall rules)

### 4. Start All Services

From the `Dyson_WOApp` directory:

```bash
cd E:\RepoInno\Dyson_WODemo\Dyson_WOApp
docker-compose up -d
```

This will start:
- Backend API (port 8000)
- Frontend UI (port 3000)
- n8n Workflow (port 5678)

### 5. Initialize Database

Run database initialization and seed data:

```bash
# Initialize database schema
docker-compose exec backend python -m app.scripts.init_db

# Generate 75 test machines
docker-compose exec backend python -m app.scripts.seed_data
```

### 6. Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **n8n Workflows**: http://localhost:5678 (credentials: admin / admin123)

## Test Data Distribution

The seed script generates **75 test machines** with the following distribution:

| Status      | Count | Percentage | Description              |
|-------------|-------|------------|--------------------------|
| **Overdue** | 15    | 20%        | Next PM date in the past |
| **Due Soon**| 25    | 33%        | Next PM within 30 days   |
| **OK**      | 35    | 47%        | Next PM > 30 days away   |

PM Frequency Distribution:
- Monthly: 30 machines
- Bimonthly: 25 machines
- Yearly: 20 machines

Additional test data:
- 5 locations (Zone A through Zone E)
- 10 suppliers with email addresses
- 3-8 maintenance history records per machine

## n8n Workflow Setup

### 1. Access n8n Dashboard

Navigate to http://localhost:5678 and login:
- Username: `admin`
- Password: `admin123`

### 2. Import Workflow

1. Click **"Workflows"** in the left sidebar
2. Click **"Import from File"**
3. Select `E:\RepoInno\Dyson_WODemo\Dyson_Workflow\workflows\daily_pm_checker.json`
4. Click **"Import"**

### 3. Configure Workflow

1. Open the imported workflow **"Daily PM Checker"**
2. Click on **"HTTP Request - Get Machines"** node
3. Verify URL: `http://backend:8000/api/v1/machines`
4. Update other HTTP nodes if needed (should auto-configure via Docker network)

### 4. Activate Workflow

1. Toggle the **"Active"** switch in the top-right corner
2. The workflow will run daily at 01:00 AM
3. To test manually, click **"Execute Workflow"**

### 5. Configure Email Notifications (Optional)

If you want n8n to send emails:
1. Click on **"Send Email"** node
2. Configure SMTP credentials
3. OR use the backend notification service (recommended)

## Using the System

### Machine Dashboard

1. Navigate to http://localhost:3000
2. View summary cards showing machine counts by status
3. Filter machines by status (All, Overdue, Due Soon, OK)
4. Click on a machine card to view details

### Triggering AI Decision

1. From the Machine Dashboard, click on any machine
2. Click **"Get AI Decision"** button
3. View AI decision result:
   - Decision: CREATE_WORK_ORDER, SEND_NOTIFICATION, or WAIT
   - Priority: Low, Medium, or High
   - Confidence: 0.0 to 1.0
   - Explanation: AI reasoning

### Approving Work Orders

1. Navigate to **"Work Orders"** tab
2. Filter by **"Pending Approval"** status
3. Click the **green checkmark** icon
4. Enter approver name
5. Click **"Approve"**

### Monitoring AI Decisions

View recent AI decisions and audit trail:
```bash
# Via API
curl http://localhost:8000/api/v1/ai/decisions/recent?limit=10

# Or check database
docker-compose exec mssql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P 'YourStrong@Passw0rd' -d dyson_pm -Q "SELECT TOP 10 * FROM ai_decisions ORDER BY created_at DESC"
```

## API Endpoints

### Machines

- `GET /api/v1/machines` - List all machines (supports `pm_status` filter)
- `GET /api/v1/machines/{id}` - Get machine details with history

### Work Orders

- `GET /api/v1/work-orders` - List work orders (supports `status` filter)
- `POST /api/v1/work-orders` - Create work order
- `POST /api/v1/work-orders/{id}/approve` - Approve work order
- `POST /api/v1/work-orders/{id}/complete` - Mark as completed
- `POST /api/v1/work-orders/{id}/cancel` - Cancel work order

### AI Decisions

- `POST /api/v1/ai/decision/{machine_id}` - Get AI decision for machine
- `GET /api/v1/ai/decisions/recent` - Get recent AI decisions

Full API documentation: http://localhost:8000/docs

## Configuration

### Changing LLM Provider

Edit `Dyson_WOApp/backend/.env`:

```env
# Switch to Claude
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-your-key

# Or switch to Gemini
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-key
```

Restart backend:
```bash
docker-compose restart backend
```

### Adjusting Confidence Threshold

Edit `Dyson_WOApp/backend/.env`:

```env
# Require 80% confidence for auto-execution
CONFIDENCE_THRESHOLD=0.8
```

Lower values = more automatic work orders
Higher values = more manual reviews required

## Troubleshooting

### Database Connection Issues

**Problem**: Backend can't connect to SQL Server

**Solution**:
```bash
# Check backend logs for connection errors
docker-compose logs backend

# Verify SQL Server is accessible from Docker host
# On Windows:
ping YOUR_SQL_SERVER_HOST
telnet YOUR_SQL_SERVER_HOST 1433

# Test connection string manually
docker-compose exec backend python -c "from app.database import engine; print(engine.connect())"

# Common issues:
# 1. SQL Server firewall blocking connections
# 2. SQL Server not configured for TCP/IP connections
# 3. Wrong credentials in DATABASE_URL
# 4. Database 'dyson_pm' doesn't exist
# 5. SQL Server browser service not running (for named instances)
```

### Frontend Can't Reach Backend

**Problem**: API calls fail with network errors

**Solution**:
```bash
# Check backend is running
docker-compose logs backend

# Verify backend health
curl http://localhost:8000/health

# Check environment variable
# In frontend container, REACT_APP_API_URL should be http://localhost:8000/api/v1
```

### LLM API Errors

**Problem**: AI decisions fail with authentication errors

**Solution**:
1. Verify API key is correct in `.env`
2. Check API key has sufficient credits/quota
3. Ensure correct model name for provider
4. View backend logs: `docker-compose logs backend`

### n8n Workflow Not Running

**Problem**: Workflow doesn't execute on schedule

**Solution**:
1. Check workflow is **Active** (toggle in top-right)
2. Verify trigger node settings (cron: `0 1 * * *`)
3. Test manually with **"Execute Workflow"**
4. Check n8n logs: `docker-compose logs n8n`

### Email Notifications Not Sending

**Problem**: No emails received

**Solution**:
1. Check SMTP configuration in `.env`
2. For Gmail, ensure App Password is used (not regular password)
3. Verify supplier emails in database
4. Check backend logs for email errors
5. SMTP is optional - system works without it (logs will show "SMTP not configured")

### Port Conflicts

**Problem**: Port already in use

**Solution**:
```bash
# Check what's using ports
netstat -ano | findstr :3000
netstat -ano | findstr :8000
netstat -ano | findstr :1433

# Change ports in docker-compose.yml
# Example: "3001:3000" for frontend
```

## Database Management

### Connect to SQL Server

**Using SQL Server Management Studio (SSMS):**
```
Server: YOUR_SQL_SERVER_HOST
Port: 1433
Authentication: SQL Server Authentication
Login: sa (or your username)
Password: (your password)
Database: dyson_pm
```

**Using Azure Data Studio:**
```
Connection type: Microsoft SQL Server
Server: YOUR_SQL_SERVER_HOST
Authentication type: SQL Login
User name: sa (or your username)
Password: (your password)
Database: dyson_pm
```

**Using sqlcmd (command line):**
```bash
sqlcmd -S YOUR_SQL_SERVER_HOST -U sa -P 'YourPassword' -d dyson_pm
```

### Backup Database

**Using SSMS:**
1. Right-click `dyson_pm` database
2. Tasks → Back Up...
3. Select backup destination
4. Click OK

**Using T-SQL:**
```sql
BACKUP DATABASE dyson_pm
TO DISK = 'C:\Backups\dyson_pm.bak'
WITH FORMAT, INIT, NAME = 'PM - AI-Assisted Demo Full Backup';
```

### Reset Database

**WARNING: This will delete all data**

```sql
-- Connect to master database
USE master;
GO

-- Drop and recreate database
DROP DATABASE IF EXISTS dyson_pm;
GO

CREATE DATABASE dyson_pm;
GO
```

Then reinitialize:
```bash
# Run initialization script
docker-compose exec backend python -m app.scripts.init_db

# Generate test data
docker-compose exec backend python -m app.scripts.seed_data
```

## Development

### Running Backend Locally

```bash
cd Dyson_WOApp/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Frontend Locally

```bash
cd Dyson_WOApp/frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Running Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend npm test
```

## Project Structure

```
Dyson_WODemo/
├── Docs/
│   └── prd_ai_assisted_preventive_maintenance_poc.md
├── Dyson_WOApp/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── schemas/             # Pydantic validation schemas
│   │   │   ├── routers/             # FastAPI route handlers
│   │   │   ├── services/            # Business logic layer
│   │   │   │   ├── llm_providers/   # LLM abstraction (OpenAI, Claude, Gemini)
│   │   │   │   ├── ai_service.py    # AI decision engine
│   │   │   │   ├── machine_service.py
│   │   │   │   ├── work_order_service.py
│   │   │   │   └── notification_service.py
│   │   │   ├── config.py            # Pydantic settings
│   │   │   ├── database.py          # SQLAlchemy setup
│   │   │   └── main.py              # FastAPI app
│   │   ├── scripts/
│   │   │   ├── init_db.py           # Database initialization
│   │   │   └── seed_data.py         # Test data generation
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── .env.example
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/          # Reusable components
│   │   │   ├── pages/               # Page components
│   │   │   │   ├── MachineDashboard.jsx
│   │   │   │   ├── MachineDetail.jsx
│   │   │   │   └── WorkOrderView.jsx
│   │   │   ├── services/            # API client layer
│   │   │   ├── hooks/               # Custom React hooks
│   │   │   ├── utils/               # Utility functions
│   │   │   ├── App.js
│   │   │   └── index.js
│   │   ├── public/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   └── package.json
│   └── docker-compose.yml
├── Dyson_Workflow/
│   ├── workflows/
│   │   └── daily_pm_checker.json
│   └── README.md
└── README.md (this file)
```

## Security Considerations

**For POC Only - Not Production Ready**

This POC includes the following security limitations:

- No authentication/authorization implemented
- No HTTPS/TLS encryption
- SQL Server SA account may be used (use dedicated service accounts in production)
- Database credentials in environment variables
- API keys in environment variables
- No rate limiting
- No input sanitization (SQL injection protected by SQLAlchemy ORM)
- SQL Server may be exposed to network (ensure proper firewall rules)

**For production deployment**, implement:
- OAuth 2.0 / JWT authentication
- HTTPS with valid certificates
- Secrets management (Azure Key Vault, AWS Secrets Manager)
- RBAC (Role-Based Access Control)
- API rate limiting
- Input validation and sanitization
- Network security groups
- Regular security audits

## Performance Considerations

- **Database**: Add indexes on frequently queried fields (already included in models)
- **LLM Calls**: Cache AI decisions for same machine state (not implemented in POC)
- **Frontend**: Lazy loading for large machine lists (not implemented in POC)
- **n8n Batching**: Currently processes 5 machines per batch (configurable)

## Cost Estimates

**LLM API Costs** (approximate for 75 machines):

| Provider | Model            | Cost per Decision | Daily (75 machines) | Monthly  |
|----------|------------------|-------------------|---------------------|----------|
| OpenAI   | GPT-4            | ~$0.02            | ~$1.50              | ~$45     |
| Anthropic| Claude 3.5 Sonnet| ~$0.01            | ~$0.75              | ~$23     |
| Google   | Gemini 1.5 Pro   | ~$0.005           | ~$0.38              | ~$11     |

*Note: Actual costs vary based on prompt length and response tokens*

## License

This is a POC project for demonstration purposes.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review API documentation: http://localhost:8000/docs
3. Check Docker logs: `docker-compose logs <service-name>`
4. Review PRD: `Docs/prd_ai_assisted_preventive_maintenance_poc.md`

## Acknowledgments

- **FastAPI** - Modern Python web framework
- **React** - UI library
- **Material-UI** - React component library
- **n8n** - Workflow automation platform
- **OpenAI, Anthropic, Google** - LLM providers
