# External SQL Server Setup Guide

This guide provides detailed instructions for connecting the PM - AI-Assisted Demo application to an external MS SQL Server instance.

## Prerequisites

- MS SQL Server 2017 or later (or Azure SQL Database)
- Network connectivity between Docker host and SQL Server
- SQL Server credentials with database creation permissions

## Step-by-Step Setup

### 1. Prepare SQL Server

#### Option A: Local SQL Server Instance

**Enable TCP/IP Protocol:**

1. Open **SQL Server Configuration Manager**
2. Navigate to **SQL Server Network Configuration** → **Protocols for [Instance Name]**
3. Right-click **TCP/IP** → **Enable**
4. Double-click **TCP/IP** → **IP Addresses** tab
5. Scroll to **IPAll** section
6. Set **TCP Port** to `1433`
7. Click **OK**
8. Restart **SQL Server** service

**Enable SQL Server Authentication:**

1. Open **SQL Server Management Studio (SSMS)**
2. Right-click server → **Properties**
3. Select **Security** page
4. Under **Server authentication**, select **SQL Server and Windows Authentication mode**
5. Click **OK**
6. Restart SQL Server service

**Configure Firewall:**

```powershell
# Windows Firewall - Allow SQL Server port
New-NetFirewallRule -DisplayName "SQL Server" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow
```

#### Option B: Azure SQL Database

1. **Create Azure SQL Database:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Create new **SQL Database**
   - Database name: `dyson_pm`
   - Choose pricing tier (Basic tier is sufficient for POC)
   - Note the **Server name** (e.g., `yourserver.database.windows.net`)

2. **Configure Firewall Rules:**
   - Go to SQL Database → **Set server firewall**
   - Add rule for your Docker host IP address
   - Or enable **Allow Azure services and resources to access this server**

3. **Get Connection String:**
   - Go to SQL Database → **Connection strings**
   - Select **ODBC**
   - Copy and modify for Python pyodbc format

### 2. Create Database

Connect to SQL Server and create the database:

**Using SSMS:**

1. Connect to your SQL Server instance
2. Right-click **Databases** → **New Database...**
3. Database name: `dyson_pm`
4. Click **OK**

**Using sqlcmd:**

```bash
sqlcmd -S YOUR_SERVER_HOST -U sa -P 'YourPassword' -Q "CREATE DATABASE dyson_pm"
```

**Using Azure Data Studio:**

1. Connect to SQL Server
2. Right-click server → **New Query**
3. Execute:
```sql
CREATE DATABASE dyson_pm;
GO
```

### 3. Configure Application Connection

#### Get Your Connection String

**Format:**
```
mssql+pyodbc://USERNAME:PASSWORD@HOST:PORT/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&PARAMETERS
```

**Examples:**

**Local SQL Server (Windows Authentication not supported - use SQL Auth):**
```
mssql+pyodbc://sa:YourPassword@localhost:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Local SQL Server (by IP):**
```
mssql+pyodbc://sa:YourPassword@192.168.1.100:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Local SQL Server (by hostname):**
```
mssql+pyodbc://sa:YourPassword@sqlserver.company.local:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Azure SQL Database:**
```
mssql+pyodbc://username@yourserver:password@yourserver.database.windows.net:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
```

**Named Instance:**
```
mssql+pyodbc://sa:YourPassword@localhost\\INSTANCENAME:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

#### Update .env File

Edit `backend/.env`:

```env
DATABASE_URL=mssql+pyodbc://sa:YourPassword@YOUR_HOST:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Important Parameters:**

- `TrustServerCertificate=yes` - Use for self-signed certificates (dev/test)
- `Encrypt=yes` - Force encryption (required for Azure SQL)
- `driver=ODBC+Driver+18+for+SQL+Server` - ODBC driver version

### 4. Test Connection

**From Docker Host (before starting containers):**

Install SQL Server tools:
```bash
# Windows - Download SQL Server Management Studio or Azure Data Studio

# Test connection via sqlcmd
sqlcmd -S YOUR_HOST -U sa -P 'YourPassword' -Q "SELECT @@VERSION"
```

**From Backend Container:**

Start only the backend service:
```bash
cd Dyson_WOApp
docker-compose up -d backend
```

Test connection:
```bash
docker-compose exec backend python -c "from app.database import engine; conn = engine.connect(); print('Connection successful!'); conn.close()"
```

If successful, you'll see: `Connection successful!`

### 5. Initialize Database Schema

Run the database initialization script:

```bash
docker-compose exec backend python -m app.scripts.init_db
```

Expected output:
```
Database initialized successfully.
Tables created: machines, maintenance_history, work_orders, ai_decisions, workflow_logs
```

### 6. Verify Tables Created

Connect to SQL Server and verify:

```sql
USE dyson_pm;
GO

-- List all tables
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE';
GO

-- Should show:
-- machines
-- maintenance_history
-- work_orders
-- ai_decisions
-- workflow_logs
```

## Troubleshooting

### Cannot Connect to SQL Server

**Error:** `[Microsoft][ODBC Driver 18 for SQL Server]TCP Provider: No connection could be made`

**Solutions:**
1. Check SQL Server is running:
   ```powershell
   Get-Service -Name MSSQL*
   ```
2. Verify TCP/IP is enabled (see Step 1A)
3. Check firewall allows port 1433
4. Ping the SQL Server host from Docker host
5. Test with telnet: `telnet YOUR_HOST 1433`

### Authentication Failed

**Error:** `Login failed for user 'sa'`

**Solutions:**
1. Verify SQL Server Authentication is enabled
2. Check password is correct
3. Ensure user exists and has permissions:
   ```sql
   -- Create new user if needed
   CREATE LOGIN dyson_user WITH PASSWORD = 'StrongPassword123!';
   GO
   USE dyson_pm;
   GO
   CREATE USER dyson_user FOR LOGIN dyson_user;
   GO
   ALTER ROLE db_owner ADD MEMBER dyson_user;
   GO
   ```

### Certificate Trust Issues

**Error:** `SSL Provider: The certificate chain was issued by an authority that is not trusted`

**Solutions:**
1. Add `TrustServerCertificate=yes` to connection string
2. Or install proper SSL certificate on SQL Server

### Named Instance Connection Issues

**Error:** `Cannot connect to HOSTNAME\\INSTANCENAME`

**Solutions:**
1. Ensure SQL Server Browser service is running
2. Use port number instead of instance name:
   ```
   mssql+pyodbc://sa:Pass@hostname:1435/dyson_pm?driver=...
   ```
3. Find instance port:
   ```sql
   -- Run on SQL Server
   SELECT local_tcp_port
   FROM sys.dm_exec_connections
   WHERE session_id = @@SPID;
   ```

### Docker Container Can't Reach SQL Server

**Problem:** Backend connects from host but not from container

**Solutions:**

1. **Use host network mode** (Windows/Mac):

   Edit `docker-compose.yml`:
   ```yaml
   backend:
     network_mode: "host"
     # ... rest of config
   ```

2. **Use host.docker.internal** (Docker Desktop):

   In `.env`:
   ```env
   DATABASE_URL=mssql+pyodbc://sa:Pass@host.docker.internal:1433/dyson_pm?driver=...
   ```

3. **Use Docker host IP**:

   Find Docker host IP:
   ```bash
   ipconfig  # Windows - look for vEthernet (WSL) or main adapter IP
   ```

   Use that IP in connection string:
   ```env
   DATABASE_URL=mssql+pyodbc://sa:Pass@192.168.1.100:1433/dyson_pm?driver=...
   ```

### Azure SQL Specific Issues

**Error:** `Client with IP address 'X.X.X.X' is not allowed to access the server`

**Solution:**
1. Go to Azure Portal → SQL Database → Firewall settings
2. Add firewall rule for your IP address
3. Or temporarily enable "Allow Azure services"

**Error:** `Login failed for user '<token-identified principal>'`

**Solution:**
- Azure SQL requires Encrypt=yes:
  ```
  DATABASE_URL=mssql+pyodbc://user@server:pass@server.database.windows.net:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
  ```

## Connection String Reference

### Standard Parameters

| Parameter | Description | Values | Example |
|-----------|-------------|--------|---------|
| driver | ODBC driver name | `ODBC Driver 18 for SQL Server` | Required |
| TrustServerCertificate | Trust self-signed certs | `yes`, `no` | Use `yes` for dev |
| Encrypt | Force encryption | `yes`, `no`, `optional` | `yes` for Azure |
| MultiSubnetFailover | Failover support | `yes`, `no` | Use for SQL clusters |
| ApplicationIntent | Read-only routing | `ReadWrite`, `ReadOnly` | Default: ReadWrite |

### Example Configurations

**Development (local, self-signed cert):**
```
mssql+pyodbc://sa:Password@localhost:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Production (valid SSL cert):**
```
mssql+pyodbc://sa:Password@sqlserver.company.com:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
```

**Azure SQL:**
```
mssql+pyodbc://admin@myserver:SecurePass123@myserver.database.windows.net:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
```

**With connection pooling:**
```
mssql+pyodbc://sa:Password@localhost:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&pool_size=10&max_overflow=20
```

## Security Best Practices

### 1. Use Dedicated Service Account

Don't use `sa` in production. Create dedicated account:

```sql
-- Create login for application
CREATE LOGIN dyson_pm_app WITH PASSWORD = 'SecureRandomPassword123!';
GO

-- Create user in database
USE dyson_pm;
GO
CREATE USER dyson_pm_app FOR LOGIN dyson_pm_app;
GO

-- Grant minimal permissions
ALTER ROLE db_datareader ADD MEMBER dyson_pm_app;  -- Read data
ALTER ROLE db_datawriter ADD MEMBER dyson_pm_app;  -- Write data
GO

-- Grant execute on stored procedures (if any)
GRANT EXECUTE TO dyson_pm_app;
GO
```

Update connection string:
```
mssql+pyodbc://dyson_pm_app:SecureRandomPassword123@...
```

### 2. Use Secrets Management

For production, don't store credentials in `.env`:

**Azure Key Vault:**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://myvault.vault.azure.net/", credential=credential)
database_url = client.get_secret("DatabaseConnectionString").value
```

**Docker Secrets:**
```yaml
# docker-compose.yml
services:
  backend:
    secrets:
      - db_connection
secrets:
  db_connection:
    external: true
```

### 3. Network Security

- Use private network / VPN for SQL Server access
- Don't expose SQL Server port to internet
- Use SSL/TLS encryption (Encrypt=yes)
- Enable SQL Server firewall
- Implement network security groups (Azure)

### 4. Regular Backups

Schedule automated backups:

```sql
-- Create backup job
BACKUP DATABASE dyson_pm
TO DISK = 'C:\Backups\dyson_pm_FULL.bak'
WITH INIT, COMPRESSION;
```

## Performance Tuning

### Connection Pooling

SQLAlchemy automatically manages connection pool. Tune via environment:

```env
# In .env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

Update `database.py`:
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

### Monitoring Connections

```sql
-- View active connections
SELECT
    session_id,
    login_name,
    host_name,
    program_name,
    status,
    last_request_end_time
FROM sys.dm_exec_sessions
WHERE database_id = DB_ID('dyson_pm');
```

## Additional Resources

- [SQL Server Network Configuration](https://docs.microsoft.com/en-us/sql/database-engine/configure-windows/configure-a-server-to-listen-on-a-specific-tcp-port)
- [Azure SQL Database Connection](https://docs.microsoft.com/en-us/azure/azure-sql/database/connect-query-content-reference-guide)
- [SQLAlchemy MS SQL Server Dialect](https://docs.sqlalchemy.org/en/14/dialects/mssql.html)
- [pyodbc Documentation](https://github.com/mkleehammer/pyodbc/wiki)
