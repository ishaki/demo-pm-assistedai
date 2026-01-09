# Quick Start - Dyson PM System Deployment

## First Time Setup (5 minutes)

### 1. Copy files to server
```bash
scp -r Dyson_WOApp user@test-server:/home/user/
```

### 2. Configure environment
```bash
cd ~/Dyson_WOApp
cp .env.production.example .env
nano .env  # Update with your values
```

**Critical settings:**
- `DATABASE_URL` - Your database connection
- `OPENAI_API_KEY` - Your LLM API key
- `REACT_APP_API_URL` - http://YOUR_SERVER_IP:8000/api/v1
- `N8N_PASSWORD` - Change from default!

### 3. Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

Done! Open `http://YOUR_SERVER_IP:3000` in browser.

---

## Common Commands

### Start/Stop
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Restart a specific service
docker-compose -f docker-compose.prod.yml restart backend
```

### View Logs
```bash
# All logs (live)
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 50 lines
docker-compose -f docker-compose.prod.yml logs --tail=50
```

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Check Status
```bash
# Container status
docker-compose -f docker-compose.prod.yml ps

# Health check
curl http://localhost:8000/health

# Resource usage
docker stats
```

---

## Troubleshooting

### Frontend can't connect to backend
```bash
# 1. Check .env file
cat .env | grep REACT_APP_API_URL

# 2. Rebuild frontend with correct API URL
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

### Database connection failed
```bash
# Test database connection
docker exec -it dyson_backend_prod python -c "from app.database import check_db_connection; print(check_db_connection())"
```

### View detailed logs
```bash
# Backend errors
docker-compose -f docker-compose.prod.yml logs backend | grep ERROR

# All container logs
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Reset everything
```bash
docker-compose -f docker-compose.prod.yml down -v
docker system prune -a
./deploy.sh
```

---

## Access URLs

- **Frontend**: http://YOUR_SERVER_IP:3000
- **Backend API**: http://YOUR_SERVER_IP:8000
- **API Documentation**: http://YOUR_SERVER_IP:8000/docs
- **n8n Workflow**: http://YOUR_SERVER_IP:5678

---

## Security Checklist

- [ ] Changed n8n password in .env
- [ ] Updated CORS_ORIGINS with your server IP
- [ ] Set DEBUG=False in .env
- [ ] Database credentials are secure
- [ ] Firewall ports configured (3000, 8000, 5678)

---

For detailed instructions, see **DEPLOYMENT.md**
