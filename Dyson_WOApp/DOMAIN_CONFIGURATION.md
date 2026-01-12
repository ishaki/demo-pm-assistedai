# Domain Configuration Guide

This guide explains how to configure the application with a custom domain name.

## Prerequisites

- A registered domain name (e.g., `your-domain.com`)
- DNS configured to point to your server's IP address
- SSL certificate (optional but recommended for production)

## Configuration Scenarios

### Scenario 1: Single Domain with Ports (Simplest)

Use your domain with different ports for each service.

**DNS Configuration:**
```
A record: your-domain.com → YOUR_SERVER_IP
```

**`.env` Configuration:**
```env
# Backend accessible at: https://your-domain.com:8000
CORS_ORIGINS=https://your-domain.com

# Frontend accessible at: https://your-domain.com:3000
REACT_APP_API_URL=https://your-domain.com:8000/api/v1

# n8n accessible at: https://your-domain.com:5678
N8N_WEBHOOK_URL=https://your-domain.com:5678/
```

**Firewall Configuration:**
```bash
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
sudo ufw allow 5678/tcp  # n8n
```

### Scenario 2: Subdomains (Recommended)

Use subdomains for each service with standard HTTPS port (443).

**DNS Configuration:**
```
A record: your-domain.com     → YOUR_SERVER_IP
A record: api.your-domain.com → YOUR_SERVER_IP
A record: n8n.your-domain.com → YOUR_SERVER_IP
```

**`.env` Configuration:**
```env
# Backend accessible at: https://api.your-domain.com
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Frontend accessible at: https://your-domain.com
REACT_APP_API_URL=https://api.your-domain.com/api/v1

# n8n accessible at: https://n8n.your-domain.com
N8N_WEBHOOK_URL=https://n8n.your-domain.com/
```

**Requires:** Reverse proxy (nginx/traefik) configuration - see below.

### Scenario 3: Path-Based Routing

Use a single domain with path-based routing.

**DNS Configuration:**
```
A record: your-domain.com → YOUR_SERVER_IP
```

**`.env` Configuration:**
```env
CORS_ORIGINS=https://your-domain.com

# Frontend at: https://your-domain.com/
# Backend at: https://your-domain.com/api/v1/
# n8n at: https://your-domain.com/n8n/
REACT_APP_API_URL=https://your-domain.com/api/v1

N8N_WEBHOOK_URL=https://your-domain.com/n8n/
```

**Requires:** Reverse proxy with path rewriting - see below.

## Reverse Proxy Setup (Nginx)

For Scenarios 2 & 3, you need a reverse proxy. Here's an nginx configuration:

### Install Nginx

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

### Scenario 2: Nginx Configuration (Subdomains)

Create `/etc/nginx/sites-available/dyson-pm`:

```nginx
# Frontend - Main domain
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API - api subdomain
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# n8n - n8n subdomain
server {
    listen 80;
    server_name n8n.your-domain.com;

    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Scenario 3: Nginx Configuration (Path-Based)

Create `/etc/nginx/sites-available/dyson-pm`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend (root path)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # n8n
    location /n8n/ {
        proxy_pass http://localhost:5678/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Enable Nginx Configuration

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/dyson-pm /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### Enable HTTPS with Let's Encrypt (Recommended)

```bash
# For Scenario 2 (subdomains)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com -d api.your-domain.com -d n8n.your-domain.com

# For Scenario 3 (single domain)
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

## Step-by-Step Setup

### 1. Update `.env` File on Server

```bash
cd /path/to/Dyson_WOApp
nano .env
```

Update with your domain configuration (see scenarios above).

### 2. Update `docker-compose.prod.yml` Ports (Optional)

If using reverse proxy, you can change ports to only bind to localhost:

```yaml
services:
  backend:
    ports:
      - "127.0.0.1:8000:8000"  # Only accessible from localhost

  frontend:
    ports:
      - "127.0.0.1:3000:80"

  n8n:
    ports:
      - "127.0.0.1:5678:5678"
```

### 3. Rebuild Frontend

The `REACT_APP_API_URL` is baked into the build, so you must rebuild:

```bash
cd /path/to/Dyson_WOApp
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Configure Reverse Proxy (if using Scenarios 2 or 3)

Follow the nginx configuration steps above.

### 5. Update DNS

Point your domain's A records to your server's IP address. Wait for DNS propagation (can take up to 48 hours, usually much faster).

### 6. Verify Configuration

```bash
# Test backend API
curl https://api.your-domain.com/health
# or
curl https://your-domain.com:8000/health

# Test frontend
curl https://your-domain.com

# Check CORS
curl -H "Origin: https://your-domain.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS https://api.your-domain.com/api/v1/machines
```

## Example: Complete Setup with Domain

Let's say your domain is `pm.example.com` and your server IP is `203.0.113.50`.

### DNS Setup
```
A record: pm.example.com     → 203.0.113.50
A record: api.pm.example.com → 203.0.113.50
A record: n8n.pm.example.com → 203.0.113.50
```

### `.env` Configuration
```env
DATABASE_URL=mssql+pyodbc://sa:YourPassword@192.168.0.18,2433/AIHarvest_Dyson_Demo?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-actual-key
CONFIDENCE_THRESHOLD=0.7
PM_DUE_DAYS=30
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=True
DEBUG=False

# Domain configuration
CORS_ORIGINS=https://pm.example.com,https://www.pm.example.com
REACT_APP_API_URL=https://api.pm.example.com/api/v1
N8N_WEBHOOK_URL=https://n8n.pm.example.com/

N8N_USER=admin
N8N_PASSWORD=your-secure-password
TIMEZONE=America/New_York
```

### Deploy
```bash
cd /path/to/Dyson_WOApp

# Rebuild with new domain configuration
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d

# Setup nginx (see nginx config above)
sudo nano /etc/nginx/sites-available/dyson-pm
sudo ln -s /etc/nginx/sites-available/dyson-pm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Enable HTTPS
sudo certbot --nginx -d pm.example.com -d www.pm.example.com -d api.pm.example.com -d n8n.pm.example.com
```

### Access
- Frontend: https://pm.example.com
- Backend API: https://api.pm.example.com/api/v1
- API Docs: https://api.pm.example.com/docs
- n8n: https://n8n.pm.example.com

## Troubleshooting

### CORS Errors
- Ensure `CORS_ORIGINS` includes your frontend domain
- Check browser console for exact error
- Verify backend logs: `docker-compose -f docker-compose.prod.yml logs backend`

### Frontend Can't Connect to Backend
- Check `REACT_APP_API_URL` is correct in `.env`
- Rebuild frontend after changing `.env`
- Verify backend is accessible: `curl https://api.your-domain.com/health`

### SSL/HTTPS Issues
- Ensure certbot ran successfully
- Check nginx error logs: `sudo tail -f /var/log/nginx/error.log`
- Verify ports 80 and 443 are open in firewall

### DNS Not Resolving
- Check DNS propagation: `nslookup your-domain.com`
- Wait up to 48 hours for full propagation
- Use `dig` to verify: `dig your-domain.com +short`

## Security Recommendations

1. **Always use HTTPS in production**
2. **Change default n8n password**
3. **Use strong database passwords**
4. **Keep API keys secure** (never commit to git)
5. **Configure firewall** to only allow necessary ports
6. **Regular security updates**: `sudo apt update && sudo apt upgrade`
7. **Enable rate limiting** in nginx for API endpoints
8. **Use environment-specific `.env` files** (never use development keys in production)

## Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx Reverse Proxy Guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
