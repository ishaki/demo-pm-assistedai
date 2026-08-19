#!/bin/bash
#
# Build a deployment package for the AI Harvest WO app.
#
# Produces dist/aiharvest-wo-app-<date>.tar.gz containing the app source, its
# Dockerfiles, the production Compose file, and the runbook -- everything the
# target host needs to build and run. Ships source rather than images so the
# target builds against its own architecture; the ODBC driver layer is the only
# slow part.
#
# Deliberately EXCLUDED:
#   .env                        - holds live secrets; never travels in a package
#   docker-compose.override.yml - local dev SQL Server, would override prod
#   node_modules, build         - reinstalled/rebuilt inside the image
#   __pycache__, *.pyc          - stale bytecode
#   AIHarvest_Workflow          - n8n runs on a separate server
#
# Usage: ./make_deployment_package.sh [version-suffix]

set -euo pipefail

cd "$(dirname "$0")"

VERSION="${1:-$(date +%Y%m%d)}"
NAME="aiharvest-wo-app-${VERSION}"
STAGE="dist/${NAME}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo "Building deployment package: ${NAME}"
echo ""

# Refuse to build if the source tree is missing what we expect, rather than
# shipping a package that fails on the server.
for required in \
    AIHarvest_WOApp/docker-compose.prod.yml \
    AIHarvest_WOApp/deploy.sh \
    AIHarvest_WOApp/deploy-app.sh \
    AIHarvest_WOApp/DEPLOY_RUNBOOK.md \
    AIHarvest_WOApp/.env.production.example \
    AIHarvest_WOApp/backend/Dockerfile.prod \
    AIHarvest_WOApp/backend/requirements.txt \
    AIHarvest_WOApp/frontend/Dockerfile \
    AIHarvest_WOApp/frontend/package.json ; do
    if [ ! -f "$required" ]; then
        echo -e "${RED}Missing required file: ${required}${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓${NC} Source tree looks complete"

rm -rf "$STAGE"
mkdir -p "$STAGE"

# Copy the app, dropping build artefacts and anything secret.
tar cf - \
    --exclude='node_modules' \
    --exclude='build' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.pytest_cache' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='docker-compose.override.yml' \
    --exclude='*.log' \
    --exclude='.vs' \
    --exclude='.DS_Store' \
    AIHarvest_WOApp | ( cd "$STAGE" && tar xf - )

echo -e "${GREEN}✓${NC} App source copied"

# Surface the runbook at the top level so it is the first thing seen.
cp AIHarvest_WOApp/DEPLOY_RUNBOOK.md "$STAGE/README_DEPLOY.md"

# Fail loudly if a secret slipped through. A package is copied around and
# archived; a leaked key in one is effectively public.
if [ -f "$STAGE/AIHarvest_WOApp/.env" ]; then
    echo -e "${RED}ABORT: .env made it into the package${NC}"
    exit 1
fi

# Length thresholds are set so real keys match but documentation placeholders
# do not: a live Anthropic key runs ~95 chars past the sk-ant-api03- prefix,
# while "sk-ant-your-actual-key-here" is far shorter. The second filter drops
# anything that still reads as a placeholder.
SECRET_HITS=$(grep -rhoE 'sk-ant-api03-[A-Za-z0-9_-]{80,}|sk-proj-[A-Za-z0-9_-]{40,}' "$STAGE" 2>/dev/null \
    | grep -viE 'your|xxx|here|actual|example|placeholder|redacted|paste' || true)

if [ -n "$SECRET_HITS" ]; then
    echo -e "${RED}ABORT: a live-looking API key was found in the package.${NC}"
    echo "Matched in:"
    grep -rlE 'sk-ant-api03-[A-Za-z0-9_-]{80,}|sk-proj-[A-Za-z0-9_-]{40,}' "$STAGE" 2>/dev/null | sed 's/^/  /'
    exit 1
fi
echo -e "${GREEN}✓${NC} No secrets in package"

# Record what was built, so a server can be traced back to a commit.
{
    echo "package:  ${NAME}"
    echo "built:    $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "branch:   $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'n/a')"
    echo "commit:   $(git rev-parse HEAD 2>/dev/null || echo 'n/a')"
    echo "dirty:    $(if git diff --quiet 2>/dev/null; then echo no; else echo YES; fi)"
    echo "contents: app only (backend + frontend). n8n and SQL Server not included."
} > "$STAGE/PACKAGE_INFO.txt"

echo -e "${GREEN}✓${NC} Build metadata written"

tar czf "dist/${NAME}.tar.gz" -C dist "$NAME"
rm -rf "$STAGE"

SIZE=$(du -h "dist/${NAME}.tar.gz" | cut -f1)

echo ""
echo "========================================="
echo -e "${GREEN}Package built${NC}"
echo "========================================="
echo "  dist/${NAME}.tar.gz  (${SIZE})"
echo ""
echo "Next steps:"
echo "  scp dist/${NAME}.tar.gz <user>@192.168.0.33:~/"
echo "  ssh <user>@192.168.0.33"
echo "  tar xzf ${NAME}.tar.gz && cd ${NAME}/AIHarvest_WOApp"
echo ""
echo -e "${YELLOW}The package contains NO .env.${NC} Copy .env.production.example to"
echo ".env on the server and set DATABASE_URL, ANTHROPIC_API_KEY, CORS_ORIGINS,"
echo "and REACT_APP_API_URL. See README_DEPLOY.md."
echo ""
