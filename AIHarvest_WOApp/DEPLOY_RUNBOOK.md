# Deployment Runbook — AI Harvest® WO Automation → 192.168.0.33

Step-by-step runbook for deploying the **app only** (FastAPI backend + React
frontend) to the Linux Docker host at `192.168.0.33`.

**Scope**

| Component | Deployed here? | Notes |
|---|---|---|
| FastAPI backend (`:8000`) | Yes | Built from `backend/Dockerfile.prod` |
| React frontend (`:3000`) | Yes | Built from `frontend/Dockerfile`, served by nginx |
| n8n workflows (`:5678`) | **No** | Already running on a separate server — see [Step 8](#step-8-point-the-existing-n8n-at-this-backend) |
| MS SQL Server | **No** | External. You must supply a reachable instance — see [Step 4](#step-4-decide-where-the-database-lives). `deploy-app.sh` never creates or alters it |

Everything below assumes you are starting from your own workstation, not the
server.

---

## Step 0 — What you need before you start

Have these four things to hand. Missing any of them blocks the deployment:

1. **SSH access** to `192.168.0.33` (username + key or password, and sudo if
   Docker needs root).
2. **A SQL Server instance** reachable from `192.168.0.33` on port 1433, with a
   database created and credentials that can create tables. See Step 4.
3. **The Anthropic API key.** Copy it from your local
   `AIHarvest_WOApp/.env` (`ANTHROPIC_API_KEY=`). It is deliberately **not**
   included in the deployment package — see [Step 5](#step-5-configure-env).
4. **The deployment package**, `aiharvest-wo-app-<date>.tar.gz`. Build it with
   `./make_deployment_package.sh` from the repo root if you do not have it.

---

## Step 1 — Connect to the server

From your workstation:

```bash
ssh <your-user>@192.168.0.33
```

On Windows, use PowerShell (OpenSSH is built in), Git Bash, or PuTTY. If you use
a key:

```bash
ssh -i ~/.ssh/your_key <your-user>@192.168.0.33
```

Confirm you are on the right box before continuing:

```bash
hostname -I     # should include 192.168.0.33
uname -a
```

---

## Step 2 — Verify Docker on the server

```bash
docker --version
docker compose version
```

Both must succeed. Notes:

- If `docker compose version` fails but `docker-compose --version` works, the
  host has legacy Compose v1. `deploy.sh` detects this and falls back
  automatically; just use `docker-compose` in place of `docker compose` in any
  command you run by hand.
- If `docker` needs `sudo`, either prefix every command with `sudo` or add
  yourself to the docker group and reconnect:

  ```bash
  sudo usermod -aG docker $USER
  exit          # then SSH back in — group changes need a new login
  ```

Check the ports the app needs are free:

```bash
sudo ss -tulpn | grep -E ':(3000|8000)\s' || echo "3000 and 8000 are free"
```

---

## Step 3 — Copy the package to the server

Run this **from your workstation**, not the server. Open a second terminal, or
`exit` the SSH session first.

```bash
scp aiharvest-wo-app-<date>.tar.gz <your-user>@192.168.0.33:~/
```

Then back on the server:

```bash
cd ~
tar xzf aiharvest-wo-app-<date>.tar.gz
cd aiharvest-wo-app/AIHarvest_WOApp
ls              # you should see docker-compose.prod.yml, backend/, frontend/
```

> **No network route for scp?** Use `rsync -avz --progress` for a resumable
> transfer, or transfer via whatever artifact store you already use. The package
> is plain source — around 1–2 MB, since `node_modules` and build output are
> excluded.

---

## Step 4 — Decide where the database lives

The app requires MS SQL Server. It does **not** ship one. Pick one of these two
paths.

### Option A — Point at an existing SQL Server (preferred)

If your organisation already runs SQL Server, create the database and use its
address. On the SQL host:

```sql
CREATE DATABASE aiharvest_pm;
GO
```

Then verify from `192.168.0.33` that the port is actually reachable — this is
the single most common cause of a failed first deploy:

```bash
# Replace with your SQL host
nc -zv <sql-host> 1433
```

If that times out, fix it before going further: SQL Server needs TCP/IP enabled,
SQL Authentication turned on, and the firewall open to `192.168.0.33`. See
`EXTERNAL_SQL_SETUP.md` for the full checklist.

### Option B — Run SQL Server in Docker on this same host

Acceptable for a demo or test deployment. Not recommended for production data —
it puts the database on the same host as the app with no backup story.

```bash
docker run -d --name aiharvest_mssql \
  -e ACCEPT_EULA=Y \
  -e 'MSSQL_SA_PASSWORD=<a-strong-password>' \
  -e MSSQL_PID=Developer \
  -p 1433:1433 \
  -v mssql_data:/var/opt/mssql \
  --restart unless-stopped \
  mcr.microsoft.com/mssql/server:2022-latest

# Wait ~30s for startup, then create the database
docker exec aiharvest_mssql /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P '<a-strong-password>' -C \
  -Q "IF DB_ID('aiharvest_pm') IS NULL CREATE DATABASE aiharvest_pm;"
```

The backend runs in its own Compose network, so `localhost` in `DATABASE_URL`
would point at the *backend container*, not the database. Attach the database
container to the app network and address it by name — do this **after** Step 6,
since the network is created by the first `docker compose up`:

```bash
docker network ls | grep agenticai          # find the exact name
docker network connect aiharvest_woapp_agenticai-demo-network aiharvest_mssql
```

Then in `.env`:

```env
DATABASE_URL=mssql+pyodbc://sa:<password>@aiharvest_mssql:1433/aiharvest_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

Recreate the backend afterwards so it picks up the change:
`docker compose -f docker-compose.prod.yml up -d backend`.

> Prefer this over pointing at a host-gateway IP such as `172.17.0.1`. That
> address is the *default* bridge gateway; a Compose project gets its own
> user-defined network with a different gateway, so a hard-coded IP often
> silently fails to route.

---

## Step 5 — Configure `.env`

```bash
cp .env.production.example .env
nano .env
```

Set these values. The three marked **critical** will break the deployment if
wrong.

```env
# --- Database ---
DATABASE_URL=mssql+pyodbc://sa:<password>@<sql-host>:1433/aiharvest_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# --- AI provider (see the section below) ---
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-api03-<paste-your-key-here>
LLM_MODEL=
OPENAI_API_KEY=
GOOGLE_API_KEY=

# --- CRITICAL: baked into the frontend build at image build time ---
REACT_APP_API_URL=http://192.168.0.33:8000/api/v1

# --- CRITICAL: without this the browser cannot call the API ---
CORS_ORIGINS=http://192.168.0.33:3000

# --- Application ---
DEBUG=False
CONFIDENCE_THRESHOLD=0.7
PM_DUE_DAYS=30

# --- Email (optional; leave blank to disable notifications) ---
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=True
```

Three things that catch people out:

- **`REACT_APP_API_URL` is compiled into the JavaScript bundle at build time**,
  not read at runtime. Changing it later requires a frontend rebuild
  (`docker compose -f docker-compose.prod.yml build --no-cache frontend`), not a
  restart. It must be the address a *browser* can reach — `192.168.0.33`, never
  `localhost`.
- **`CORS_ORIGINS` must list the frontend origin exactly**, including scheme and
  port. `http://192.168.0.33:3000` and `http://192.168.0.33` are different
  origins to a browser.
- **`DEBUG=False`.** With `DEBUG=True` SQLAlchemy logs every statement, which
  floods the logs and leaks query contents.

### Demo reset page

The page at `/demo-reset`, reached from the sidebar copyright, deletes every row
in `machines`, `maintenance_history`, `work_orders`, `ai_decisions` and
`workflow_logs`, then reseeds. There is no other authentication in this
application, so these two variables are the whole of its access control.

| Variable | Value | Why |
|---|---|---|
| `DEMO_RESET_ENABLED` | `True` on a demo box, **`False` on anything holding real data** | `False` makes the endpoint answer 403 and do nothing. |
| `DEMO_RESET_TOKEN` | 32+ random characters | The passphrase the page asks for. Left blank while enabled, the endpoint answers **503** for every request rather than standing open. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `DEMO_ADMIN_EMAIL` | e.g. `you@example.com` | Prefilled on the page; a reset writes it to every machine's `admin_email`. |
| `DEMO_SUPPLIER_EMAIL` | e.g. `supplier@example.com` | Prefilled on the page; a reset writes it to every machine's `supplier_email`. |

Changing any of these needs the container **recreated**, not restarted — the
same caveat as the API keys below.

Lock the file down — it holds your database password, API key and reset token:

```bash
chmod 600 .env
```

### AI API key configuration

This is the part that changed most recently, so read it even if you have
deployed this app before.

| Variable | Value | Why |
|---|---|---|
| `LLM_PROVIDER` | `claude` | **Not `anthropic`.** The accepted values are the keys of `provider_map` in `app/services/llm_providers/__init__.py`: `openai`, `claude`, `gemini`. Anything else fails at startup with `Unknown LLM provider`. Older copies of `.env.production.example` incorrectly said "anthropic". |
| `ANTHROPIC_API_KEY` | `sk-ant-api03-…` | Required when `LLM_PROVIDER=claude`. Copy it from your local `.env`. |
| `LLM_MODEL` | *(blank)* | Blank uses the provider default, **`claude-sonnet-5`**. Only set this to pin a different model. |

Supporting changes already baked into this package:

- `docker-compose.prod.yml` now forwards `LLM_MODEL` to the backend. It was
  declared in `config.py` but never passed through, so the model could not be
  changed without editing code.
- `claude_provider.py` sends **no `temperature`** and reads the **first text
  block** of the response rather than `content[0]`. Both are required by current
  Claude models: sampling parameters are rejected with a 400, and with thinking
  on the first content block is a thinking block with no text. `max_tokens` is
  8192 because that ceiling covers thinking as well as the reply.
- `deploy.sh` validates that `LLM_PROVIDER` is one of the three valid values and
  that the matching key is non-empty, so a typo fails in seconds instead of
  surfacing when someone clicks **Get AI Decision**.

**Billing:** the key must belong to an account with credit. A key with a zero
balance authenticates fine and then fails every request with
`Your credit balance is too low to access the Anthropic API`. If AI decisions
fail after deployment, check this before debugging anything else.

---

## Step 6 — Deploy

There are two scripts. Use `deploy-app.sh` unless you have a specific reason
not to.

| Script | What it does |
|---|---|
| `deploy-app.sh` | **App only.** Builds and recreates backend + frontend, and issues **no database DDL at all**. Every other container on the host — n8n, a local SQL Server — keeps running untouched. |
| `deploy.sh` | The original. Runs `docker compose down` first, which stops **every** service in the compose file including n8n, and lets the backend create missing tables on startup. Can also bring up n8n via `DEPLOY_SERVICES`. Note the `DATABASE_URL` parsing fault in [Troubleshooting](#deploysh-says-database_url-is-not-set-when-it-plainly-is). |

**First deployment**, against an empty database — the tables need creating:

```bash
chmod +x deploy-app.sh
./deploy-app.sh --with-db-init
```

**Every deployment after that** — the schema already exists, so leave it alone:

```bash
./deploy-app.sh
```

Without `--with-db-init` the backend runs with `DB_AUTO_CREATE_TABLES=False`: no
`CREATE TABLE`, no `ALTER`, no seed script, no new database. The only database
traffic is a read-only `SELECT 1` liveness probe. The script prints which mode
it resolved before doing anything, and the health check afterwards reports what
the running backend actually does — so you can confirm rather than assume.

The build takes 5–10 minutes on the first run; installing the Microsoft ODBC
driver is the slow part. Later runs reuse the layer cache. Changed source and
changed build args invalidate it on their own, so `--no-cache` is only for when
you suspect a stale cache.

Neither script starts n8n by default, since it runs on your other server — two
schedulers would race on the same webhooks. `deploy-app.sh` cannot start it at
all. If you do want it on this host, use the original script:

```bash
DEPLOY_SERVICES="backend frontend n8n" ./deploy.sh
```

Other `deploy-app.sh` options: `--backend-only`, `--frontend-only`, `--no-cache`,
and `--skip-build` (recreate the containers so a changed `.env` is re-read,
without rebuilding). `./deploy-app.sh --help` lists them all.

<details>
<summary>Manual equivalent, if you would rather not use the script</summary>

```bash
docker compose -f docker-compose.prod.yml build backend frontend
DB_AUTO_CREATE_TABLES=False docker compose -f docker-compose.prod.yml \
  up -d --no-deps --force-recreate backend frontend
docker compose -f docker-compose.prod.yml ps backend frontend
```

Three things to keep: the explicit service names, because a bare `up -d` would
also start n8n; `DB_AUTO_CREATE_TABLES=False`, which is what suppresses the
startup DDL and is baked into the container when it is created; and the absence
of `down`, which would stop every service in the file, n8n included.
</details>

---

## Step 7 — Initialize and seed the database

**First deployment only.** `deploy-app.sh` deliberately does not create tables
unless asked, so this is now an explicit step.

If you deployed with `--with-db-init`, the backend created them on startup.
Confirm:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep -i "Database initialization"
# expected: Database initialization completed
```

If you deployed without it, the log says so instead, and you create the tables
yourself. Safe to re-run — it only adds what is missing:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep -i "skipping automatic table creation"
docker compose -f docker-compose.prod.yml exec backend python scripts/init_db.py
```

Neither route alters or drops an existing table. But `create_all` is **not a
migration**: a new column on an existing table is added by neither route, and
needs a manual `ALTER TABLE`.

**Demo data — skip both commands on a deployment holding real data.** They are
destructive: each clears its tables first.

```bash
# 75 machines, 10 suppliers, 5 zones, maintenance history.
# --yes skips the confirmation prompt, which a runbook should not block on.
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_data.py --yes

# 45 work orders across every status, plus the AI decisions behind them
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_work_orders.py
```

Run `seed_data.py` first — `seed_work_orders.py` attaches work orders to
existing machines and exits with an error if there are none.

Both take arguments now (`--count`, `--approved`, `--reserve-overdue`, …); run
either with `--help` for the list.

**Between demo runs, prefer the reset page** at `/demo-reset`, reached from the
sidebar copyright. It does both steps in one transaction and lets you set the
notification addresses and per-status counts without a shell. It needs
`DEMO_RESET_TOKEN` set in the backend environment — see Step 5 — and
answers 503 until it is. To keep the endpoint inert on this deployment
altogether, set `DEMO_RESET_ENABLED=False`.

---

## Step 8 — Point the existing n8n at this backend

Your n8n server needs two changes to talk to this deployment.

1. **In the n8n workflows**, update the backend base URL to
   `http://192.168.0.33:8000`. The affected workflows are `daily_pm_checker`,
   `process_single_machine`, and `check_maintenance_email` — check every HTTP
   Request node for a hard-coded host.

2. **Add the n8n server to `CORS_ORIGINS`** only if a browser on that host loads
   the UI. Server-to-server calls from n8n are not subject to CORS, so in most
   setups this is unnecessary.

Verify the route in the other direction — from the n8n host:

```bash
curl -s http://192.168.0.33:8000/health
```

If that fails, open the firewall on `192.168.0.33` (Step 9).

---

## Step 9 — Firewall

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 3000/tcp    # frontend
sudo ufw allow 8000/tcp    # backend API
sudo ufw reload
sudo ufw status

# firewalld (RHEL/CentOS)
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

Port 5678 is **not** needed — n8n is not deployed here.

To restrict access to your LAN rather than opening the ports broadly:

```bash
sudo ufw allow from 192.168.0.0/24 to any port 3000 proto tcp
sudo ufw allow from 192.168.0.0/24 to any port 8000 proto tcp
```

---

## Step 10 — Verify the deployment

Run all five. Every one should pass before you hand the URL to anyone.

```bash
# 1. Containers up and healthy
docker compose -f docker-compose.prod.yml ps

# 2. Backend healthy and connected to the database
curl -s http://localhost:8000/health
# expect: {"status":"healthy", ... "database":"connected", "llm_provider":"claude"}

# 3. Data is present
curl -s "http://localhost:8000/api/v1/machines/?limit=1"

# 4. Frontend served
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000    # expect 200

# 5. AI provider actually works (makes a real, billable API call)
curl -s -X POST http://localhost:8000/api/v1/ai/decision/1
# expect JSON with decision / confidence / explanation
```

Then from a browser **on another machine** — this is what catches
`REACT_APP_API_URL` and CORS mistakes, which never show up in curl on the host:

- Frontend: <http://192.168.0.33:3000>
- API docs: <http://192.168.0.33:8000/docs>

Open the browser devtools Network tab and confirm the dashboard's XHR calls go
to `http://192.168.0.33:8000/api/v1/...` and return 200.

---

## Operations

```bash
# Logs (follow)
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs --tail=200 backend

# Restart / stop / start
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml stop
docker compose -f docker-compose.prod.yml start

# Stop and remove containers (data lives in SQL Server, so this is safe)
docker compose -f docker-compose.prod.yml down

# Resource usage
docker stats --no-stream
```

### Changing configuration

| What changed | Action |
|---|---|
| `ANTHROPIC_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `DATABASE_URL`, `CORS_ORIGINS`, SMTP | `./deploy-app.sh --backend-only --skip-build` — recreates the container so it re-reads `.env`, with the schema gate still off. A `restart` is **not** enough; it reuses the old environment. A bare `up -d backend` also works but re-enables table auto-creation, since the flag is only set by the script. |
| `REACT_APP_API_URL` | Rebuild the frontend: `docker compose -f docker-compose.prod.yml build --no-cache frontend && docker compose -f docker-compose.prod.yml up -d frontend`. It is compiled into the bundle. |
| Application code | Re-deploy: see below. |

### Deploying a new version

```bash
# On the server, keep the current config
cd ~/aiharvest-wo-app/AIHarvest_WOApp
cp .env ~/aiharvest.env.backup

# Extract the new package alongside, then restore config
cd ~ && tar xzf aiharvest-wo-app-<new-date>.tar.gz
cp ~/aiharvest.env.backup ~/aiharvest-wo-app/AIHarvest_WOApp/.env

cd ~/aiharvest-wo-app/AIHarvest_WOApp
./deploy-app.sh
```

An app upgrade needs no database step. `deploy-app.sh` issues no DDL, so the
schema you have is the schema you keep.

### Rollback

Images from the previous build remain on the host until pruned, so the fastest
rollback is to re-tag and restart. Confirm what you have:

```bash
docker images | grep aiharvest
```

If the previous image is gone, re-extract the previous package and re-run
`./deploy-app.sh`. Rolling the app back never requires a database restore: the
app only ever adds tables, and only when asked to.

---

## Troubleshooting

### Frontend loads but shows no data / "Network Error"

Almost always `REACT_APP_API_URL` or `CORS_ORIGINS`.

```bash
# What did the bundle actually get built with?
docker compose -f docker-compose.prod.yml exec frontend \
  grep -ro "http://[^\"']*api/v1" /usr/share/nginx/html/static/js/ | head -3

# What does the backend allow?
docker compose -f docker-compose.prod.yml exec backend printenv CORS_ORIGINS
```

If the baked URL is wrong, rebuild the frontend — a restart will not help.

A genuine backend error now returns a readable JSON message with CORS headers
attached, so if the browser still reports a bare "Network Error" with no status,
the request is not reaching the backend at all — suspect the firewall or a wrong
host in the URL, not the application.

### AI decisions fail

Check the message first, it is specific:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep -iA3 "error"
curl -s -X POST http://localhost:8000/api/v1/ai/decision/1
```

| Message | Cause |
|---|---|
| `ANTHROPIC_API_KEY is not configured` | Key missing/empty in `.env`, or the container was restarted rather than recreated. Run `up -d backend`. |
| `Unknown LLM provider: 'anthropic'` | `LLM_PROVIDER` must be `claude`. |
| `credit balance is too low` | Valid key, unfunded account. Add credit. |
| `authentication_error` | Key is wrong, revoked, or truncated on copy. Check its length. |
| 400 mentioning `temperature` | An older `claude_provider.py` is deployed. This package's version sends no temperature. |

### `deploy.sh` says `DATABASE_URL is not set` when it plainly is

`deploy.sh` reads `.env` with `source`, which applies shell rules to a file that
is not a shell script. The connection string in `.env.production.example` is
unquoted and contains an ampersand:

```env
DATABASE_URL=mssql+pyodbc://...?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

`source` reads that as "assign up to the `&`, in the background", so the value
never reaches the script and validation rejects a perfectly good `.env`. Two
ways out — either quote the value:

```env
DATABASE_URL="mssql+pyodbc://...&TrustServerCertificate=yes"
```

or use `deploy-app.sh`, which parses `.env` literally the way Compose does and
is unaffected. Compose itself was never confused by this, so a container that
did start has the correct URL.

### Database connection failed

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "from app.database import check_db_connection; print(check_db_connection())"
# expect: True
```

`False` means the URL, credentials, or network path is wrong. Test raw
reachability from the host with `nc -zv <sql-host> 1433`. Remember the container
cannot reach a host-local database via `localhost` — see Step 4.

### Backend container restarts repeatedly

```bash
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

A malformed `DATABASE_URL` is the usual cause — startup raises before uvicorn
binds.

### Port already in use

```bash
sudo ss -tulpn | grep -E ':(3000|8000)\s'
```

Either stop the conflicting process or remap the host side in
`docker-compose.prod.yml` (e.g. `"8080:8000"`), remembering to update
`REACT_APP_API_URL` and `CORS_ORIGINS` to match and rebuild the frontend.

---

## Security checklist

- [ ] `.env` is `chmod 600` and never committed
- [ ] `DEBUG=False`
- [ ] Database account has only the permissions it needs, not `sa`
- [ ] `CORS_ORIGINS` lists real origins only — no `*`
- [ ] Firewall scoped to your LAN rather than open to the world
- [ ] API key came from a secure channel, not email or chat
- [ ] The app is behind a reverse proxy with TLS if it is reachable beyond the
      LAN (see `DOMAIN_CONFIGURATION.md`)
- [ ] Whoever holds the Anthropic key knows it is billable

---

## Reference

| Document | Covers |
|---|---|
| `DEPLOYMENT.md` | Generic Docker deployment, reverse proxy, monitoring, backups |
| `EXTERNAL_SQL_SETUP.md` | SQL Server setup, firewall, connection strings, troubleshooting |
| `DOMAIN_CONFIGURATION.md` | Custom domains, TLS/HTTPS, subdomain layout |
| `LOCAL_INSTALLATION_GUIDE.md` | Running without Docker, for development |
| `.env.production.example` | Every supported variable, annotated |
| `./deploy-app.sh --help` | App-only deployment options |
