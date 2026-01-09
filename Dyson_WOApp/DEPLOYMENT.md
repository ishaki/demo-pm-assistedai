# Deployment Guide - Dyson PM System

This guide explains how to deploy the Dyson AI-Assisted Preventive Maintenance system to a test server using Docker.

## Prerequisites

### On Your Test Server:
- Ubuntu 20.04+ or similar Linux distribution
- Docker installed (20.10+)
- Docker Compose installed (2.0+)
- At least 4GB RAM
- Port 3000, 8000, and 5678 available
- Access to SQL Server database

### Installation of Docker (if not installed):
```bash
# Update packages
sudo apt update
sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and log back in for group changes to take effect
```

---

## Deployment Steps

### Step 1: Transfer Files to Test Server

**Option A: Using Git (Recommended)**
```bash
# On test server
git clone <your-repository-url>
cd Dyson_WODemo/Dyson_WOApp
```

**Option B: Using SCP**
```bash
# On your local machine
scp -r E:\RepoInno\Dyson_WODemo\Dyson_WOApp user@test-server-ip:/home/user/
```

**Option C: Using rsync**
```bash
# On your local machine
rsync -avz --exclude 'node_modules' --exclude '__pycache__' E:\RepoInno\Dyson_WODemo\Dyson_WOApp/ user@test-server-ip:/home/user/dyson-app/
```

---

### Step 2: Configure Environment Variables

```bash
# On test server, navigate to app directory
cd ~/dyson-app  # or wherever you copied the files

# Copy the example environment file
cp .env.production.example .env

# Edit the .env file with your actual values
nano .env
```

**Critical values to update:**
- `DATABASE_URL` - Your SQL Server connection string
- `OPENAI_API_KEY` or relevant LLM API key
- `SMTP_USERNAME` and `SMTP_PASSWORD` - For email notifications
- `REACT_APP_API_URL` - Should point to your test server IP:8000/api/v1
- `CORS_ORIGINS` - Should include your test server IP:3000
- `N8N_PASSWORD` - Change from default!

**Example for test server at 192.168.1.100:**
```env
DATABASE_URL=mssql+pyodbc://sa:YourPassword@192.168.1.50:1433/DysonPM?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
REACT_APP_API_URL=http://192.168.1.100:8000/api/v1
CORS_ORIGINS=http://192.168.1.100:3000,http://localhost:3000
```

---

### Step 3: Build and Start the Application

```bash
# Build all images (this may take 5-10 minutes)
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check if all containers are running
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

**Expected output:**
```
NAME                    STATUS              PORTS
dyson_backend_prod      Up (healthy)        0.0.0.0:8000->8000/tcp
dyson_frontend_prod     Up (healthy)        0.0.0.0:3000->80/tcp
dyson_n8n_prod          Up                  0.0.0.0:5678->5678/tcp
```

---

### Step 4: Verify Deployment

**1. Check Backend API:**
```bash
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","app_name":"Dyson PM System","version":"1.0.0",...}
```

**2. Check Frontend:**
- Open browser: `http://your-test-server-ip:3000`
- You should see the Dyson PM login/dashboard

**3. Check n8n:**
- Open browser: `http://your-test-server-ip:5678`
- Login with credentials from .env file
- Import workflows from `../Dyson_Workflow/workflows/`

**4. Check Container Logs:**
```bash
# Backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Frontend logs
docker-compose -f docker-compose.prod.yml logs frontend

# n8n logs
docker-compose -f docker-compose.prod.yml logs n8n
```

---

### Step 5: Initialize Database (First Time Only)

The database tables should be created automatically on first startup. Verify by checking backend logs:

```bash
docker-compose -f docker-compose.prod.yml logs backend | grep "Database initialization"

# Should see: "Database initialization completed"
```

If tables are not created, you can manually run:
```bash
# Access backend container
docker exec -it dyson_backend_prod bash

# Inside container
python -c "from app.database import init_db; init_db()"

# Exit container
exit
```

---

## Firewall Configuration

If your test server has a firewall, open the required ports:

```bash
# UFW (Ubuntu)
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
sudo ufw allow 5678/tcp  # n8n
sudo ufw reload

# firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=5678/tcp
sudo firewall-cmd --reload
```

---

## Management Commands

### Start/Stop Services
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml stop

# Start all services
docker-compose -f docker-compose.prod.yml start

# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Stop and remove containers
docker-compose -f docker-compose.prod.yml down

# Stop and remove containers + volumes (⚠️ deletes n8n data)
docker-compose -f docker-compose.prod.yml down -v
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Update Application
```bash
# Pull latest code (if using git)
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Check Resource Usage
```bash
# Container stats
docker stats

# Disk usage
docker system df
```

### Backup n8n Data
```bash
# Backup n8n workflows and settings
docker run --rm -v dyson_woapp_n8n_data:/data -v $(pwd):/backup alpine tar czf /backup/n8n-backup-$(date +%Y%m%d).tar.gz /data

# Restore n8n data
docker run --rm -v dyson_woapp_n8n_data:/data -v $(pwd):/backup alpine tar xzf /backup/n8n-backup-YYYYMMDD.tar.gz -C /
```

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs backend

# Common issues:
# 1. Database connection failed - check DATABASE_URL
# 2. Port already in use - check with: sudo netstat -tulpn | grep LISTEN
# 3. Permission denied - check file ownership: ls -la
```

### Frontend Can't Connect to Backend
```bash
# 1. Check REACT_APP_API_URL in .env
# 2. Check CORS_ORIGINS in .env
# 3. Rebuild frontend with new env:
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

### Database Connection Issues
```bash
# Test database connectivity from backend container
docker exec -it dyson_backend_prod bash
python -c "from app.database import check_db_connection; print(check_db_connection())"

# Should print: True
```

### Reset Everything (⚠️ Destructive)
```bash
# Stop and remove all containers, volumes, and images
docker-compose -f docker-compose.prod.yml down -v
docker system prune -a --volumes

# Rebuild from scratch
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

---

## Production Best Practices (Optional for Test)

### 1. Use Reverse Proxy (Nginx)
Instead of exposing ports directly, use Nginx as reverse proxy:

```nginx
# /etc/nginx/sites-available/dyson-pm
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # n8n
    location /n8n/ {
        proxy_pass http://localhost:5678/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Enable SSL/HTTPS (Using Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Set Up Monitoring
```bash
# Install monitoring tools
docker run -d --name=prometheus -p 9090:9090 prom/prometheus
docker run -d --name=grafana -p 3001:3000 grafana/grafana
```

### 4. Automated Backups
Create a cron job for daily backups:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /home/user/dyson-app && docker run --rm -v dyson_woapp_n8n_data:/data -v /home/user/backups:/backup alpine tar czf /backup/n8n-$(date +\%Y\%m\%d).tar.gz /data
```

---

## Access URLs (After Deployment)

Replace `<test-server-ip>` with your server's IP address:

- **Frontend**: `http://<test-server-ip>:3000`
- **Backend API**: `http://<test-server-ip>:8000`
- **API Docs**: `http://<test-server-ip>:8000/docs`
- **n8n Workflow**: `http://<test-server-ip>:5678`
- **Health Check**: `http://<test-server-ip>:8000/health`

---

## Support

If you encounter issues:
1. Check container logs: `docker-compose -f docker-compose.prod.yml logs -f`
2. Verify environment variables in `.env`
3. Check firewall settings
4. Ensure database is accessible from test server
5. Review this deployment guide

---

## Security Checklist

- [ ] Changed default n8n password
- [ ] Database credentials are secure
- [ ] API keys are not committed to version control
- [ ] Firewall is configured properly
- [ ] CORS origins are restricted
- [ ] Debug mode is disabled (`DEBUG=False`)
- [ ] Using strong passwords for all services
- [ ] Regular backups are configured
