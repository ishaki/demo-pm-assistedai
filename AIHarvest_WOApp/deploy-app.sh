#!/bin/bash
#
# AIHarvest PM System - APP-ONLY deployment (FastAPI backend + React frontend).
#
# The one guarantee this script makes: it does not touch the database.
#
# Not merely "it does not delete data" -- it issues no schema statements at all.
# No database is created, no table is created, altered or dropped, and no seed
# script is run. The only database traffic is the backend's read-only SELECT 1
# liveness probe.
#
# That needs enforcing in two places, because a shell script alone cannot
# promise it:
#
#   1. Here. Only backend and frontend are ever built or started, by name. There
#      is no "compose down", so anything else already running on the host (n8n,
#      a SQL Server container) is left strictly alone.
#
#   2. In the backend. app/main.py calls Base.metadata.create_all() on startup,
#      once per uvicorn worker, on every restart. This script exports
#      DB_AUTO_CREATE_TABLES=False, which skips that call entirely. Pass
#      --with-db-init to allow it.
#
# Use ./deploy.sh instead for the older behaviour: whole-stack "down", schema
# auto-creation on, optional n8n.
#
# Usage:
#   ./deploy-app.sh [options]
#
#   --with-db-init    Allow the backend to create missing tables on startup.
#                     Needed for a FIRST deployment against an empty database.
#                     Additive only: create_all() never drops or alters an
#                     existing table.
#   --backend-only    Deploy only the backend.
#   --frontend-only   Deploy only the frontend.
#   --no-cache        Rebuild images from scratch. Slow (~5-10 min: the MS ODBC
#                     driver layer). Only needed if you suspect a stale cache;
#                     changed source and changed build args invalidate it on
#                     their own.
#   --skip-build      Recreate containers from existing images without building.
#                     Use after an .env change other than REACT_APP_API_URL.
#   -h, --help        Show this help.

set -euo pipefail

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.prod.yml"

WANT_BACKEND=1
WANT_FRONTEND=1
DB_INIT_REQUESTED=0
NO_CACHE=0
SKIP_BUILD=0

while [ $# -gt 0 ]; do
    case "$1" in
        --with-db-init)  DB_INIT_REQUESTED=1 ;;
        --backend-only)  WANT_FRONTEND=0 ;;
        --frontend-only) WANT_BACKEND=0 ;;
        --no-cache)      NO_CACHE=1 ;;
        --skip-build)    SKIP_BUILD=1 ;;
        -h|--help)
            sed -n '3,42p' "$0" | sed -e 's/^#$//' -e 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run ./deploy-app.sh --help for usage."
            exit 1
            ;;
    esac
    shift
done

TARGETS=""
[ "$WANT_BACKEND" -eq 1 ]  && TARGETS="$TARGETS backend"
[ "$WANT_FRONTEND" -eq 1 ] && TARGETS="$TARGETS frontend"
TARGETS="$(echo "$TARGETS" | xargs)"

if [ -z "$TARGETS" ]; then
    echo -e "${RED}Error: --backend-only and --frontend-only are mutually exclusive.${NC}"
    exit 1
fi

echo "========================================="
echo "AIHarvest PM System - App-Only Deployment"
echo "========================================="
echo ""

# --------------------------------------------------------------------------
# Preflight
# --------------------------------------------------------------------------

if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Copy the template and fill it in first:"
    echo "  cp .env.production.example .env"
    echo "  nano .env"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: $COMPOSE_FILE not found.${NC}"
    echo "Run this script from the AIHarvest_WOApp directory."
    exit 1
fi

# Read .env literally, the way Docker Compose does -- deliberately NOT with
# `source`, which applies shell rules to a file that is not a shell script.
# The MS SQL connection string in .env.production.example is unquoted and
# contains an ampersand:
#
#   DATABASE_URL=mssql+pyodbc://...?driver=ODBC+Driver+18...&TrustServerCertificate=yes
#
# `source` reads that as "assign up to the &, in the background", so the parent
# shell ends up with DATABASE_URL empty and a stray TrustServerCertificate=yes.
# Validation then rejects a perfectly good .env. A value containing $ or # goes
# wrong in its own way.
#
# Nothing read here is exported. Compose does its own parsing of .env when it
# builds the container environment, and an exported value would take precedence
# over the file -- so a mangled parse here would silently reach the container.
# These values are for validation and reporting only. The one exception is
# DB_AUTO_CREATE_TABLES, exported further down on purpose.
env_get() {
    local key="$1"
    local line val found sq dq
    val=""
    found=0
    sq="'"
    dq='"'
    # The CR of a .env saved on Windows is stripped on the way in. Left in
    # place it becomes the last character of every value, which quietly
    # changes what DEBUG or a URL compares equal to.
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ''|'#'*) continue ;;
        esac
        line="${line#export }"
        case "$line" in
            "$key"=*) ;;
            *) continue ;;
        esac
        val="${line#*=}"
        found=1
        # Strip one layer of matching surrounding quotes, as Compose does.
        case "$val" in
            "$dq"*"$dq") val="${val#$dq}"; val="${val%$dq}" ;;
            "$sq"*"$sq") val="${val#$sq}"; val="${val%$sq}" ;;
        esac
        # Keep scanning: a later definition of the same key wins, as in dotenv.
    done < <(tr -d '\r' < .env)
    [ "$found" -eq 1 ] && printf '%s' "$val"
    return 0
}

CFG_DATABASE_URL="$(env_get DATABASE_URL)"
CFG_CORS_ORIGINS="$(env_get CORS_ORIGINS)"
CFG_REACT_APP_API_URL="$(env_get REACT_APP_API_URL)"
CFG_LLM_PROVIDER="$(env_get LLM_PROVIDER)"
CFG_ANTHROPIC_API_KEY="$(env_get ANTHROPIC_API_KEY)"
CFG_OPENAI_API_KEY="$(env_get OPENAI_API_KEY)"
CFG_GOOGLE_API_KEY="$(env_get GOOGLE_API_KEY)"
CFG_DEBUG="$(env_get DEBUG)"
CFG_DB_AUTO_CREATE_TABLES="$(env_get DB_AUTO_CREATE_TABLES)"

echo -e "${GREEN}OK${NC} Read .env"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "See DEPLOYMENT.md for instructions."
    exit 1
fi

# Compose v2 ships as a docker subcommand; fall back to the standalone v1
# binary for older hosts.
if docker compose version &> /dev/null; then
    DC="docker compose -f $COMPOSE_FILE"
    echo -e "${GREEN}OK${NC} Using Docker Compose v2"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose -f $COMPOSE_FILE"
    echo -e "${GREEN}OK${NC} Using Docker Compose v1 (standalone)"
else
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "See DEPLOYMENT.md for instructions."
    exit 1
fi

# The backend-side half of the no-DDL guarantee lives in the source tree. If
# this package predates it, the image we are about to build calls create_all()
# on startup no matter what this script exports -- so refuse, rather than
# promise something we cannot deliver.
if [ "$WANT_BACKEND" -eq 1 ] && [ "$SKIP_BUILD" -eq 0 ]; then
    if ! grep -q DB_AUTO_CREATE_TABLES backend/app/config.py 2>/dev/null \
       || ! grep -q DB_AUTO_CREATE_TABLES backend/app/main.py 2>/dev/null; then
        echo -e "${RED}X${NC} This source tree does not support DB_AUTO_CREATE_TABLES."
        echo "    backend/app/main.py would call create_all() on startup regardless of"
        echo "    what this script sets, so the no-schema-changes guarantee cannot be"
        echo "    honoured. Deploy a package built from current source."
        exit 1
    fi
    echo -e "${GREEN}OK${NC} Backend supports the schema-creation switch"
fi

# Guard against a database service having been added to the compose file since
# this script was written. We only ever name backend/frontend on the command
# line, but check rather than assume.
ALL_SERVICES="$($DC config --services 2>/dev/null | tr -d '\r' | xargs || true)"
if [ -z "$ALL_SERVICES" ]; then
    echo -e "${RED}X${NC} Could not read the service list from $COMPOSE_FILE."
    echo "    Check the file and .env for syntax errors:"
    $DC config --services || true
    exit 1
fi

for t in $TARGETS; do
    case " $ALL_SERVICES " in
        *" $t "*) ;;
        *)
            echo -e "${RED}X${NC} Service '$t' is not defined in $COMPOSE_FILE."
            echo "    Services found: $ALL_SERVICES"
            exit 1
            ;;
    esac
done

DB_LIKE=""
for s in $ALL_SERVICES; do
    case "$s" in
        mssql|sqlserver|sql|postgres|postgresql|pgsql|mysql|mariadb|mongo|mongodb|db|database|redis)
            DB_LIKE="$DB_LIKE $s"
            # A data store we were also asked to deploy would mean this script is
            # provisioning storage. It must not.
            case " $TARGETS " in
                *" $s "*)
                    echo -e "${RED}X${NC} Refusing to deploy data-store service '$s'."
                    echo "    This script deploys the application only."
                    exit 1
                    ;;
            esac
            ;;
    esac
done

echo -e "${GREEN}OK${NC} Compose services: $ALL_SERVICES"
if [ -n "$DB_LIKE" ]; then
    echo -e "${YELLOW}!${NC} Data-store service(s) present in the file:$DB_LIKE"
    echo "    Not built, not started, not stopped by this script."
fi

# Worth naming explicitly, since ./deploy.sh does stop these.
UNTOUCHED=""
for s in $ALL_SERVICES; do
    case " $TARGETS " in
        *" $s "*) ;;
        *) UNTOUCHED="$UNTOUCHED $s" ;;
    esac
done

# --------------------------------------------------------------------------
# Configuration validation -- fail in seconds, not after a 10-minute build
# --------------------------------------------------------------------------

fail=0

if [ -z "$CFG_DATABASE_URL" ]; then
    echo -e "${RED}X${NC} DATABASE_URL is not set"
    fail=1
fi

if [ -z "$CFG_CORS_ORIGINS" ]; then
    echo -e "${RED}X${NC} CORS_ORIGINS is not set (the browser will be unable to call the API)"
    fail=1
fi

# Baked into the bundle at build time, so it only matters when building the
# frontend -- but a wrong value here is the most common deployment fault.
if [ "$WANT_FRONTEND" -eq 1 ] && [ -z "$CFG_REACT_APP_API_URL" ]; then
    echo -e "${RED}X${NC} REACT_APP_API_URL is not set (it is baked into the frontend build)"
    fail=1
fi

# LLM_PROVIDER must be a provider_map key with its matching key present. A
# mismatch otherwise surfaces only when a user clicks Get AI Decision.
if [ "$WANT_BACKEND" -eq 1 ]; then
    case "${CFG_LLM_PROVIDER:-openai}" in
        claude)
            [ -z "$CFG_ANTHROPIC_API_KEY" ] && { echo -e "${RED}X${NC} LLM_PROVIDER=claude but ANTHROPIC_API_KEY is empty"; fail=1; }
            ;;
        openai)
            [ -z "$CFG_OPENAI_API_KEY" ] && { echo -e "${RED}X${NC} LLM_PROVIDER=openai but OPENAI_API_KEY is empty"; fail=1; }
            ;;
        gemini)
            [ -z "$CFG_GOOGLE_API_KEY" ] && { echo -e "${RED}X${NC} LLM_PROVIDER=gemini but GOOGLE_API_KEY is empty"; fail=1; }
            ;;
        *)
            echo -e "${RED}X${NC} LLM_PROVIDER='${CFG_LLM_PROVIDER}' is not valid. Use: openai | claude | gemini"
            echo "    (anthropic and google are NOT accepted -- see .env.production.example)"
            fail=1
            ;;
    esac
fi

if [ "$CFG_DEBUG" = "True" ]; then
    echo -e "${YELLOW}!${NC} DEBUG=True -- this logs every SQL statement. Set DEBUG=False for production."
fi

if [ "$fail" -ne 0 ]; then
    echo ""
    echo -e "${RED}Configuration is incomplete. Fix .env and re-run.${NC}"
    exit 1
fi

echo -e "${GREEN}OK${NC} Configuration validated (LLM provider: ${CFG_LLM_PROVIDER:-openai})"

# --------------------------------------------------------------------------
# Resolve the schema switch
# --------------------------------------------------------------------------
#
# This script is authoritative: off by default, on only via --with-db-init. A
# stale DB_AUTO_CREATE_TABLES=True in .env must not quietly defeat the point of
# running this script, so say so when overriding it.

ENV_DB_INIT="$CFG_DB_AUTO_CREATE_TABLES"

if [ "$DB_INIT_REQUESTED" -eq 1 ]; then
    export DB_AUTO_CREATE_TABLES=True
else
    export DB_AUTO_CREATE_TABLES=False
fi

echo ""
if [ "$DB_INIT_REQUESTED" -eq 1 ]; then
    echo -e "${YELLOW}!${NC} --with-db-init given: the backend WILL create missing tables on startup."
    echo "    create_all() is additive -- existing tables and their data are not modified."
else
    echo -e "${BLUE}==>${NC} Database: no schema changes. DB_AUTO_CREATE_TABLES=False"
    echo "    No database created, no table created/altered/dropped, no seed script run."
    echo "    Tables must already exist. First deployment? Use --with-db-init."
    case "$ENV_DB_INIT" in
        ""|False|false|0|no|off) ;;
        *)
            echo -e "${YELLOW}!${NC} .env sets DB_AUTO_CREATE_TABLES=$ENV_DB_INIT -- overridden to False for"
            echo "    this deployment. Pass --with-db-init if you meant to allow it."
            ;;
    esac
fi

echo ""
echo -e "${BLUE}==>${NC} Deploying: $TARGETS"
if [ -n "$UNTOUCHED" ]; then
    echo -e "${BLUE}==>${NC} Left untouched (not stopped, not started):$UNTOUCHED"
fi

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
#
# There is no "compose down" anywhere in this script. down removes the
# containers for every service in the file, not just the ones named -- which is
# how a co-located n8n gets stopped and never brought back. The up -d below
# replaces the target containers in place instead.

if [ "$SKIP_BUILD" -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Skipping build (--skip-build); using existing images.${NC}"
    if [ "$WANT_BACKEND" -eq 1 ]; then
        echo -e "${YELLOW}!${NC} The no-DDL guarantee then rests on the image already built."
        echo "    The health check below reports what the running backend actually does."
    fi
else
    echo ""
    if [ "$NO_CACHE" -eq 1 ]; then
        echo -e "${YELLOW}Building images from scratch (several minutes)...${NC}"
        # shellcheck disable=SC2086
        $DC build --no-cache $TARGETS
    else
        echo -e "${YELLOW}Building images...${NC}"
        # shellcheck disable=SC2086
        $DC build $TARGETS
    fi
fi

# --------------------------------------------------------------------------
# Start
# --------------------------------------------------------------------------
#
# --no-deps        never pull in another service via depends_on.
# --force-recreate a plain restart reuses the old environment, so a changed
#                  .env would not take effect. Recreating re-reads it.

echo ""
echo -e "${YELLOW}Starting services...${NC}"
# shellcheck disable=SC2086
$DC up -d --no-deps --force-recreate $TARGETS

echo ""
echo "Container status:"
# shellcheck disable=SC2086
$DC ps $TARGETS

# --------------------------------------------------------------------------
# Verify
# --------------------------------------------------------------------------

HAVE_CURL=1
command -v curl &> /dev/null || HAVE_CURL=0
if [ "$HAVE_CURL" -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}!${NC} curl not found -- skipping health checks."
fi

HEALTH=""
if [ "$WANT_BACKEND" -eq 1 ] && [ "$HAVE_CURL" -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Waiting for the backend...${NC}"
    for i in $(seq 1 30); do
        HEALTH="$(curl -s --max-time 5 http://localhost:8000/health || true)"
        if [ -n "$HEALTH" ]; then
            echo -e "${GREEN}OK${NC} Backend responded"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo -e "${RED}X${NC} Backend health check failed after 60s"
            echo "    Check logs with: $DC logs --tail=50 backend"
        fi
        echo "  waiting... ($i/30)"
        sleep 2
    done

    if [ -n "$HEALTH" ]; then
        echo ""
        echo "Backend health:"
        echo "  $HEALTH"

        case "$HEALTH" in
            *'"database":"connected"'*)
                echo -e "${GREEN}OK${NC} Database reachable (read-only SELECT 1)"
                ;;
            *)
                echo -e "${YELLOW}!${NC} Database not reachable. The app is up but data calls will error."
                echo "    Check DATABASE_URL and reachability: nc -zv <sql-host> 1433"
                ;;
        esac

        # Confirm from outside what the running backend actually does about the
        # schema, rather than trusting what we exported.
        case "$HEALTH" in
            *'"db_auto_create_tables":false'*)
                echo -e "${GREEN}OK${NC} Confirmed: automatic table creation is OFF in the running backend"
                ;;
            *'"db_auto_create_tables":true'*)
                echo -e "${YELLOW}!${NC} The running backend has automatic table creation ON."
                ;;
            *)
                echo -e "${YELLOW}!${NC} The running backend does not report db_auto_create_tables."
                echo "    Its image predates the switch, so it creates missing tables on startup."
                echo "    Rebuild without --skip-build to get the gated version."
                ;;
        esac
    fi

    # The startup log is the direct evidence for what was or was not issued.
    echo ""
    echo "Schema activity in the startup log:"
    SCHEMA_LOG="$($DC logs --tail=200 backend 2>&1 | grep -iE 'skipping automatic table creation|Database tables created|Database initialization' || true)"
    if [ -n "$SCHEMA_LOG" ]; then
        echo "$SCHEMA_LOG" | sed 's/^/  /'
    else
        echo "  (nothing logged yet -- check $DC logs backend once it has settled)"
    fi
fi

if [ "$WANT_FRONTEND" -eq 1 ] && [ "$HAVE_CURL" -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Checking the frontend...${NC}"
    FE_OK=0
    for i in $(seq 1 10); do
        if curl -s --max-time 5 -o /dev/null http://localhost:3000; then
            FE_OK=1
            break
        fi
        sleep 2
    done
    if [ "$FE_OK" -eq 1 ]; then
        echo -e "${GREEN}OK${NC} Frontend is serving on :3000"
    else
        echo -e "${RED}X${NC} Frontend is not responding"
        echo "    Check logs with: $DC logs --tail=50 frontend"
    fi
fi

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
[ -n "$HOST_IP" ] || HOST_IP="localhost"

echo ""
echo "========================================="
echo -e "${GREEN}App deployment complete${NC}"
echo "========================================="
echo ""
[ "$WANT_FRONTEND" -eq 1 ] && echo "  Frontend:  http://${HOST_IP}:3000"
if [ "$WANT_BACKEND" -eq 1 ]; then
    echo "  Backend:   http://${HOST_IP}:8000"
    echo "  API docs:  http://${HOST_IP}:8000/docs"
fi
echo ""
if [ "$DB_INIT_REQUESTED" -eq 0 ]; then
    echo "Database: untouched. This deployment issued no DDL."
    echo ""
    echo "If tables are missing, create them explicitly:"
    echo "  $DC exec backend python scripts/init_db.py"
    echo ""
fi
echo "Seed scripts are never run by this script. They CLEAR their tables first --"
echo "do not run them on a deployment holding real data."
echo ""
echo "Useful commands:"
echo "  Logs:            $DC logs -f $TARGETS"
echo "  Restart:         $DC restart $TARGETS"
echo "  Stop app only:   $DC stop $TARGETS"
echo "  Re-read .env:    ./deploy-app.sh --skip-build"
echo ""
echo "See DEPLOY_RUNBOOK.md for the full procedure."
echo ""
