#!/bin/bash
#
# AIHarvest PM System - rebuild .env from the containers already running here.
#
# The situation this is for: the app is up on the server, but the .env that
# produced it is gone, stale, or never made it across -- deployment packages
# deliberately ship without one (see make_deployment_package.sh). Everything
# Compose interpolated is still readable from Docker, so the file can be
# reconstructed from the deployment itself instead of retyped from memory.
#
# Where each value comes from:
#   backend container   DATABASE_URL, LLM provider + keys, SMTP, CORS_ORIGINS,
#                       DEBUG, thresholds
#   frontend container  REACT_APP_API_URL. In production this is NOT a runtime
#                       variable -- it is a build arg baked into the JS bundle,
#                       so it is recovered by reading the bundle back out.
#   n8n container       N8N_USER / N8N_PASSWORD / N8N_WEBHOOK_URL / TIMEZONE,
#                       mapped back from the N8N_BASIC_AUTH_* and WEBHOOK_URL
#                       names the image actually takes.
#   compose labels      COMPOSE_PROJECT_NAME, which decides which n8n volume the
#                       next deploy attaches. Getting this wrong is what makes
#                       n8n credentials appear to vanish.
#
# What comes back is each container's CREATION-time environment: the config
# actually serving traffic. If someone edited .env after the last deploy without
# recreating the containers, this file will differ from that .env. That is the
# point -- here the containers are the source of truth, not the file.
#
# Values Compose defaulted (SMTP_HOST, PM_DUE_DAYS, DB_AUTO_CREATE_TABLES, ...)
# come back as the effective value even where the original .env omitted them.
# Writing a default explicitly changes nothing.
#
# The output holds every secret the deployment has: database password, LLM API
# key, SMTP password, n8n password. It is written 600, secrets are masked in the
# terminal summary, and an existing file is backed up rather than clobbered.
#
# Usage:
#   ./generate-env.sh [options]
#
#   -o, --output FILE   Write here instead of ./.env
#       --print         Write to stdout instead of a file. Prints every secret
#                       in the clear -- fine for `| ssh host 'cat > .env'`,
#                       not for a shared terminal.
#   -f, --force         Overwrite an existing output file. The old one is kept
#                       as FILE.bak.<timestamp> either way.
#       --backend NAME  Container name or ID to read, for when autodetection
#       --frontend NAME cannot choose: several stacks on one host, or unusual
#       --n8n NAME      names.
#       --project NAME  Only consider containers from this Compose project.
#       --no-n8n        Skip n8n entirely. Use when n8n runs on another host.
#       --no-frontend   Skip the frontend, and with it REACT_APP_API_URL.
#   -h, --help          Show this help.
#
# Exits non-zero if a value the app cannot start without could not be recovered.
# The file is still written in that case, with the gaps marked.

set -euo pipefail

cd "$(dirname "$0")"

if [ -z "${BASH_VERSINFO:-}" ] || [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
    echo "Error: this script needs bash 4 or newer (associative arrays)." >&2
    exit 1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

OUT=".env"
PRINT=0
FORCE=0
WANT_FRONTEND=1
WANT_N8N=1
NAME_BACKEND=""
NAME_FRONTEND=""
NAME_N8N=""
PROJECT=""

show_help() {
    awk '/^# Usage:/{p=1} p&&/^#/{sub(/^# ?/,""); print; next} p{exit}' "$0"
}

while [ $# -gt 0 ]; do
    case "$1" in
        -o|--output)   OUT="${2:?--output needs a path}"; shift ;;
        --print)       PRINT=1 ;;
        -f|--force)    FORCE=1 ;;
        --backend)     NAME_BACKEND="${2:?--backend needs a container}"; shift ;;
        --frontend)    NAME_FRONTEND="${2:?--frontend needs a container}"; shift ;;
        --n8n)         NAME_N8N="${2:?--n8n needs a container}"; shift ;;
        --project)     PROJECT="${2:?--project needs a name}"; shift ;;
        --no-n8n)      WANT_N8N=0 ;;
        --no-frontend) WANT_FRONTEND=0 ;;
        -h|--help)     show_help; exit 0 ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            echo "Run ./generate-env.sh --help for usage." >&2
            exit 1
            ;;
    esac
    shift
done

# Everything that is not the file itself goes to stderr, so --print can be piped
# somewhere useful without the commentary landing in the .env.
say() { echo -e "$@" >&2; }

say "========================================="
say "AIHarvest PM System - .env from running containers"
say "========================================="
say ""

if ! command -v docker &> /dev/null; then
    say "${RED}Error: Docker is not installed (or not on PATH).${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    say "${RED}Error: cannot talk to the Docker daemon.${NC}"
    say "    Start it, or add this user to the docker group, and retry."
    exit 1
fi

# --------------------------------------------------------------------------
# Finding the containers
# --------------------------------------------------------------------------
#
# Compose labels first: com.docker.compose.service is backend/frontend/n8n
# whichever compose file and container_name were used, and it survived the
# Dyson -> AIHarvest rename. Names are only the fallback, for a stack started by
# hand or with `docker run`.
#
# Running containers are preferred over stopped ones, but a stopped container is
# still worth reading: its recorded environment is exactly what it last ran with.

CONTAINER_LIST="$(docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.State}}' 2>/dev/null || true)"

label_candidates() {
    local service="$1"
    local args=(--filter "label=com.docker.compose.service=$service")
    [ -n "$PROJECT" ] && args+=(--filter "label=com.docker.compose.project=$PROJECT")
    docker ps -a "${args[@]}" --format '{{.Names}}' 2>/dev/null || true
}

name_candidates() {
    # $1 = service word, rest = exact names to try first.
    local service="$1"; shift
    local n found=""
    for n in "$@"; do
        if printf '%s\n' "$CONTAINER_LIST" | cut -f2 | grep -qxF "$n"; then
            found="$found$n"$'\n'
        fi
    done
    if [ -z "$found" ]; then
        found="$(printf '%s\n' "$CONTAINER_LIST" | cut -f2 | grep -E "(^|[_-])${service}([_-]|$)" || true)"
    fi
    printf '%s' "$found"
}

is_running() {
    [ "$(docker inspect --format '{{.State.Running}}' "$1" 2>/dev/null || echo false)" = "true" ]
}

# Echoes the chosen container name on stdout, or nothing. Never exits -- a
# missing frontend or n8n is a warning, a missing backend is for the caller to
# decide about. Returns 1 when there was no candidate at all and 2 when there
# were too many (or a named one did not exist), so the caller can say which.
pick_container() {
    local service="$1" explicit="$2"; shift 2
    local cands running c

    if [ -n "$explicit" ]; then
        if ! docker inspect "$explicit" &> /dev/null; then
            say "${RED}X${NC} No such container: $explicit"
            return 2
        fi
        printf '%s' "$explicit"
        return 0
    fi

    cands="$(label_candidates "$service")"
    [ -z "$cands" ] && cands="$(name_candidates "$service" "$@")"

    cands="$(printf '%s\n' "$cands" | sed '/^$/d' | sort -u)"
    [ -z "$cands" ] && return 1

    # Narrow to running containers when there is a choice: a live one beats the
    # remains of a previous deploy sitting next to it.
    running=""
    while IFS= read -r c; do
        [ -n "$c" ] && is_running "$c" && running="$running$c"$'\n'
    done <<< "$cands"
    [ -n "$running" ] && cands="$(printf '%s' "$running" | sed '/^$/d')"

    if [ "$(printf '%s\n' "$cands" | wc -l)" -gt 1 ]; then
        say "${RED}X${NC} Several containers could be the $service:"
        printf '%s\n' "$cands" | sed 's/^/      /' >&2
        say "    Pick one with --${service} NAME (or narrow with --project NAME)."
        return 2
    fi

    printf '%s' "$cands"
}

# --------------------------------------------------------------------------
# Reading a container's environment
# --------------------------------------------------------------------------
#
# .Config.Env comes out NUL-delimited: a value containing a newline (rare, but a
# pasted key can) would otherwise split into two bogus entries. It carries the
# image's own ENV lines too (PATH, LANG, ...); only the keys asked for below are
# ever taken, so that noise is ignored rather than filtered.

declare -A CENV=()

read_container_env() {
    local cid="$1" kv
    CENV=()
    while IFS= read -r -d '' kv; do
        case "$kv" in
            *=*) CENV["${kv%%=*}"]="${kv#*=}" ;;
        esac
    done < <(docker inspect --format '{{range .Config.Env}}{{.}}{{printf "\x00"}}{{end}}' "$cid")
}

declare -A VAL=()          # key -> recovered value
declare -A HAVE=()         # key -> 1 if recovered at all
declare -A SRC=()          # key -> where it came from, for the file's comments
declare -A MISSING_NOTE=() # key -> what to write instead, when not recovered
ORDER=()                   # keys in the order they are written
MISSING=()

want() {
    # want <out-key> <source-key> <source-label>
    local dst="$1" src="$2" from="$3"
    ORDER+=("$dst")
    SRC["$dst"]="$from"
    if [ -n "${CENV[$src]+set}" ]; then
        VAL["$dst"]="${CENV[$src]}"
        HAVE["$dst"]=1
    else
        HAVE["$dst"]=0
    fi
}

set_value() {
    # set_value <out-key> <value> <source-label>
    ORDER+=("$1")
    VAL["$1"]="$2"
    HAVE["$1"]=1
    SRC["$1"]="$3"
}

mark_missing() {
    # mark_missing <out-key> <source-label> [line to write in the file instead]
    ORDER+=("$1")
    HAVE["$1"]=0
    SRC["$1"]="$2"
    [ $# -ge 3 ] && MISSING_NOTE["$1"]="$3"
    return 0
}

# --------------------------------------------------------------------------
# Backend
# --------------------------------------------------------------------------

BACKEND=""
BACKEND_RC=0
BACKEND="$(pick_container backend "$NAME_BACKEND" aiharvest_backend_prod aiharvest_backend dyson_backend_prod dyson_backend)" || BACKEND_RC=$?

if [ -z "$BACKEND" ]; then
    if [ "$BACKEND_RC" -eq 1 ]; then
        say "${RED}X${NC} No backend container found on this host."
        say "    Looked for the label com.docker.compose.service=backend, then for"
        say "    container names containing 'backend'. Name it explicitly if it is"
        say "    called something else:  ./generate-env.sh --backend my_api"
        say ""
        say "    Containers on this host:"
        docker ps -a --format '      {{.Names}}\t{{.Image}}\t{{.Status}}' >&2 || true
    fi
    say ""
    say "${RED}Nothing to read. No file written.${NC}"
    exit 1
fi

BACKEND_STATE="$(docker inspect --format '{{.State.Status}}' "$BACKEND")"
BACKEND_IMAGE="$(docker inspect --format '{{.Config.Image}}' "$BACKEND")"
BACKEND_CREATED="$(docker inspect --format '{{.Created}}' "$BACKEND")"
COMPOSE_PROJECT="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$BACKEND" 2>/dev/null || true)"
[ "$COMPOSE_PROJECT" = "<no value>" ] && COMPOSE_PROJECT=""

say "${GREEN}OK${NC} Backend:  $BACKEND  ($BACKEND_STATE, ${COMPOSE_PROJECT:-no compose project}, $BACKEND_IMAGE)"
if [ "$BACKEND_STATE" != "running" ]; then
    say "${YELLOW}!${NC} That container is not running. Its recorded environment is still"
    say "    what it last ran with, so it is read anyway."
fi

read_container_env "$BACKEND"

want DATABASE_URL          DATABASE_URL          "$BACKEND"
want DB_AUTO_CREATE_TABLES DB_AUTO_CREATE_TABLES "$BACKEND"
want LLM_PROVIDER          LLM_PROVIDER          "$BACKEND"
want LLM_MODEL             LLM_MODEL             "$BACKEND"
want OPENAI_API_KEY        OPENAI_API_KEY        "$BACKEND"
want ANTHROPIC_API_KEY     ANTHROPIC_API_KEY     "$BACKEND"
want GOOGLE_API_KEY        GOOGLE_API_KEY        "$BACKEND"
want CONFIDENCE_THRESHOLD  CONFIDENCE_THRESHOLD  "$BACKEND"
want PM_DUE_DAYS           PM_DUE_DAYS           "$BACKEND"
want SMTP_HOST             SMTP_HOST             "$BACKEND"
want SMTP_PORT             SMTP_PORT             "$BACKEND"
want SMTP_USERNAME         SMTP_USERNAME         "$BACKEND"
want SMTP_PASSWORD         SMTP_PASSWORD         "$BACKEND"
want SMTP_FROM_EMAIL       SMTP_FROM_EMAIL       "$BACKEND"
want SMTP_USE_TLS          SMTP_USE_TLS          "$BACKEND"
want DEBUG                 DEBUG                 "$BACKEND"
want CORS_ORIGINS          CORS_ORIGINS          "$BACKEND"

# --------------------------------------------------------------------------
# Frontend: REACT_APP_API_URL
# --------------------------------------------------------------------------
#
# The production frontend is nginx serving a static build. REACT_APP_API_URL was
# consumed by `npm run build` in an earlier build stage and is not in the runtime
# environment at all -- so read it back out of the bundle it was baked into. (The
# dev compose runs CRA in node, where it is a plain env var; try that first.)

FRONTEND=""
FRONTEND_NOTE=""
FRONTEND_RC=0

if [ "$WANT_FRONTEND" -eq 1 ]; then
    FRONTEND="$(pick_container frontend "$NAME_FRONTEND" aiharvest_frontend_prod aiharvest_frontend dyson_frontend_prod dyson_frontend)" || FRONTEND_RC=$?
fi

bundle_api_url() {
    # Every absolute URL ending in /api/v1 that appears in the served files.
    local c="$1" img probe out
    probe='grep -rhoE "https?://[^\"[:space:]]+/api/v1" /usr/share/nginx/html 2>/dev/null | sort -u'
    if is_running "$c"; then
        out="$(docker exec "$c" sh -c "$probe" 2>/dev/null || true)"
    else
        # Stopped: the files still exist in the image, so read them from a
        # throwaway container rather than starting the real one.
        img="$(docker inspect --format '{{.Config.Image}}' "$c" 2>/dev/null || true)"
        [ -z "$img" ] && return 0
        out="$(docker run --rm --entrypoint sh "$img" -c "$probe" 2>/dev/null || true)"
    fi
    printf '%s' "$out"
}

if [ -n "$FRONTEND" ]; then
    say "${GREEN}OK${NC} Frontend: $FRONTEND  ($(docker inspect --format '{{.State.Status}}' "$FRONTEND"))"
    read_container_env "$FRONTEND"

    if [ -n "${CENV[REACT_APP_API_URL]-}" ]; then
        set_value REACT_APP_API_URL "${CENV[REACT_APP_API_URL]}" "$FRONTEND (environment)"
    else
        URLS="$(bundle_api_url "$FRONTEND")"
        # src/services/api.js falls back to http://localhost:8000/api/v1 when the
        # build arg is unset. If anything else is in there, that is the real one
        # and the fallback is just the untaken branch.
        REAL="$(printf '%s\n' "$URLS" | sed '/^$/d' | grep -v '^http://localhost:8000/api/v1$' || true)"
        [ -z "$REAL" ] && REAL="$(printf '%s\n' "$URLS" | sed '/^$/d')"

        if [ -z "$REAL" ]; then
            say "${YELLOW}!${NC} No API URL found in the frontend bundle."
            say "    Set REACT_APP_API_URL by hand: it is where the browser, not the"
            say "    container, reaches the backend."
            mark_missing REACT_APP_API_URL "$FRONTEND" \
                "no absolute API URL in $FRONTEND's bundle -- set this by hand"
        else
            if [ "$(printf '%s\n' "$REAL" | wc -l)" -gt 1 ]; then
                say "${YELLOW}!${NC} The frontend bundle mentions more than one API URL:"
                printf '%s\n' "$REAL" | sed 's/^/      /' >&2
                say "    Taking the first. Check it before deploying."
            fi
            set_value REACT_APP_API_URL "$(printf '%s\n' "$REAL" | head -1)" "$FRONTEND (bundle)"
            FRONTEND_NOTE="Read out of the JS bundle served by $FRONTEND -- it is a build arg, so it is not in that container's environment to read."
        fi
    fi
elif [ "$WANT_FRONTEND" -eq 1 ]; then
    if [ "$FRONTEND_RC" -eq 1 ]; then
        say "${YELLOW}!${NC} No frontend container on this host; REACT_APP_API_URL left blank."
        mark_missing REACT_APP_API_URL "no frontend container" \
            "no frontend container on this host -- set this by hand"
    else
        say "${YELLOW}!${NC} Frontend not identified (above); REACT_APP_API_URL left blank."
        mark_missing REACT_APP_API_URL "frontend not identified" \
            "frontend container not identified -- re-run with --frontend NAME"
    fi
fi

# --------------------------------------------------------------------------
# n8n
# --------------------------------------------------------------------------
#
# The image takes N8N_BASIC_AUTH_USER / _PASSWORD / WEBHOOK_URL /
# GENERIC_TIMEZONE; the compose file feeds those from N8N_USER / N8N_PASSWORD /
# N8N_WEBHOOK_URL / TIMEZONE. Map back, or the regenerated .env sets nothing and
# the next deploy quietly falls back to admin/admin123.

N8N=""
N8N_RC=0
if [ "$WANT_N8N" -eq 1 ]; then
    N8N="$(pick_container n8n "$NAME_N8N" aiharvest_n8n_prod aiharvest_n8n dyson_n8n_prod dyson_n8n)" || N8N_RC=$?
fi

if [ -n "$N8N" ]; then
    say "${GREEN}OK${NC} n8n:      $N8N  ($(docker inspect --format '{{.State.Status}}' "$N8N"))"
    read_container_env "$N8N"
    want N8N_USER        N8N_BASIC_AUTH_USER     "$N8N"
    want N8N_PASSWORD    N8N_BASIC_AUTH_PASSWORD "$N8N"
    want N8N_WEBHOOK_URL WEBHOOK_URL             "$N8N"
    want TIMEZONE        GENERIC_TIMEZONE        "$N8N"
    if [ -z "$COMPOSE_PROJECT" ]; then
        COMPOSE_PROJECT="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$N8N" 2>/dev/null || true)"
        [ "$COMPOSE_PROJECT" = "<no value>" ] && COMPOSE_PROJECT=""
    fi
elif [ "$WANT_N8N" -eq 1 ]; then
    if [ "$N8N_RC" -eq 1 ]; then
        say "${YELLOW}!${NC} No n8n container on this host; the n8n block is written as comments."
    else
        say "${YELLOW}!${NC} n8n not identified (above); the n8n block is written as comments."
    fi
fi

# --------------------------------------------------------------------------
# Formatting values the way Compose reads them back
# --------------------------------------------------------------------------
#
# Compose's .env parser is not a shell, but it is not literal either: it
# interpolates $VAR, treats " #" as the start of a comment, trims unquoted
# whitespace, and strips one layer of surrounding quotes.
#
#   plain             anything printable with none of $ # ' " \ or whitespace
#   'single quoted'   taken literally, no interpolation -- the safe wrapper
#   "double quoted"   last resort, for a value containing a single quote or a
#                     newline; \ " and newlines are escaped and a literal $ is
#                     written $$, which is what Compose unescapes back
#
# DATABASE_URL is why this matters: it is full of + & ? = : / and goes out
# plain, exactly as .env.production.example writes it.
#
# The result goes in FMT_OUT rather than on stdout: a command substitution would
# run this in a subshell, and QUOTED_ODD -- the list of values a human should
# look at -- would be lost with it.

UNSAFE_RE='[[:space:]$#'"'"'"\\]'
QUOTED_ODD=()
FMT_OUT=""

fmt_value() {
    local v="$1" k="${2:-}" e
    FMT_OUT=""
    [ -z "$v" ] && return 0
    if [[ "$v" =~ ^[[:print:]]+$ ]] && [[ ! "$v" =~ $UNSAFE_RE ]]; then
        FMT_OUT="$v"
    elif [[ "$v" =~ ^[[:print:]]+$ ]] && [[ "$v" != *"'"* ]]; then
        FMT_OUT="'$v'"
    else
        e="$v"
        e="${e//\\/\\\\}"
        e="${e//\"/\\\"}"
        e="${e//\$/\$\$}"
        e="${e//$'\r'/\\r}"
        e="${e//$'\n'/\\n}"
        QUOTED_ODD+=("${k:-?}")
        FMT_OUT="\"$e\""
    fi
    return 0
}

mask() {
    local k="$1" v="$2" len
    case "$k" in
        *API_KEY|*PASSWORD|*SECRET|*TOKEN)
            len=${#v}
            if [ "$len" -eq 0 ]; then printf '(empty)'
            elif [ "$len" -gt 16 ]; then printf '%s...%s  (%d chars)' "${v:0:6}" "${v: -4}" "$len"
            else printf '***  (%d chars)' "$len"
            fi
            ;;
        DATABASE_URL)
            # Greedy up to the LAST @, so a password containing one (P@ssw0rd)
            # is hidden whole rather than half-printed.
            printf '%s' "$v" | sed -E 's#(://[^:/@]*:).*@#\1***@#'
            ;;
        *)
            if [ -z "$v" ]; then printf '(empty)'; else printf '%s' "$v"; fi
            ;;
    esac
}

# --------------------------------------------------------------------------
# Write it
# --------------------------------------------------------------------------

if [ "$PRINT" -eq 0 ] && [ -e "$OUT" ] && [ "$FORCE" -eq 0 ]; then
    say "${RED}X${NC} $OUT already exists."
    say "    Re-run with --force to replace it (the old one is kept as a .bak),"
    say "    or write elsewhere and compare:  -o .env.from-containers"
    exit 1
fi

# 600 from the moment it exists rather than after a chmod: this file is about to
# hold the database password and the LLM key.
umask 077
OUT_DIR="$(dirname "$OUT")"
TMP="$(mktemp "$OUT_DIR/.env.generated.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

put()   { printf '%s\n' "$*" >> "$TMP"; }
blank() { printf '\n' >> "$TMP"; }

emit() {
    local k="$1" note
    if [ "${HAVE[$k]:-0}" = "1" ]; then
        fmt_value "${VAL[$k]}" "$k"
        put "$k=$FMT_OUT"
    else
        note="${MISSING_NOTE[$k]:-}"
        [ -z "$note" ] && note="not set on ${SRC[$k]:-any container}; Compose's default applies"
        put "# $k=   # $note"
        MISSING+=("$k")
    fi
}

put "# ============================================================"
put "# AIHarvest PM System - generated from the running containers"
put "# ============================================================"
put "#"
put "# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ') by generate-env.sh"
put "# Host:      $(hostname 2>/dev/null || echo unknown)"
put "# Backend:   $BACKEND  ($BACKEND_IMAGE, created $BACKEND_CREATED)"
put "# Frontend:  ${FRONTEND:-not read}"
put "# n8n:       ${N8N:-not read}"
put "#"
put "# These are the values the containers were CREATED with -- the configuration"
put "# actually serving traffic. Where the original .env left something out, what"
put "# appears here is the default Compose substituted."
put "#"
put "# Holds live secrets: mode 600, never commit it, never let it into a"
put "# deployment package. Reference for every setting: .env.production.example"
blank

put "# ==========================="
put "# DOCKER COMPOSE PROJECT NAME"
put "# ==========================="
if [ -n "$COMPOSE_PROJECT" ]; then
    DEFAULT_PROJECT="$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"
    put "# The running stack belongs to Compose project '$COMPOSE_PROJECT', which names"
    put "# its volumes and networks -- ${COMPOSE_PROJECT}_n8n_data is where n8n"
    put "# credentials and execution history live."
    if [ "$COMPOSE_PROJECT" = "$DEFAULT_PROJECT" ]; then
        put "# That matches the default derived from this directory ($DEFAULT_PROJECT),"
        put "# so it needs no setting. Left commented."
        put "# COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT"
    else
        put "# Deploying from this directory would default to '$DEFAULT_PROJECT' instead"
        put "# and attach a new, empty n8n volume. Set explicitly so the next deploy"
        put "# stays on the existing one."
        put "COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT"
    fi
else
    put "# The containers carry no Compose project label (started with docker run?),"
    put "# so there is nothing to preserve here."
fi
blank

put "# ==========================="
put "# DATABASE CONFIGURATION"
put "# ==========================="
emit DATABASE_URL
blank
put "# Captured from the running backend. deploy-app.sh forces this to False on"
put "# every run unless given --with-db-init, so False here may reflect that flag"
put "# rather than anything the old .env said."
emit DB_AUTO_CREATE_TABLES
blank

put "# ==========================="
put "# LLM PROVIDER CONFIGURATION"
put "# ==========================="
emit LLM_PROVIDER
emit LLM_MODEL
emit OPENAI_API_KEY
emit ANTHROPIC_API_KEY
emit GOOGLE_API_KEY
blank

put "# ==========================="
put "# AI DECISION THRESHOLDS"
put "# ==========================="
emit CONFIDENCE_THRESHOLD
emit PM_DUE_DAYS
blank

put "# ==========================="
put "# EMAIL CONFIGURATION"
put "# ==========================="
emit SMTP_HOST
emit SMTP_PORT
emit SMTP_USERNAME
emit SMTP_PASSWORD
emit SMTP_FROM_EMAIL
emit SMTP_USE_TLS
blank

put "# ==========================="
put "# APPLICATION SETTINGS"
put "# ==========================="
emit DEBUG
blank

put "# ==========================="
put "# CORS CONFIGURATION"
put "# ==========================="
emit CORS_ORIGINS
blank

put "# ==========================="
put "# FRONTEND CONFIGURATION"
put "# ==========================="
put "# Baked into the React build, so changing it needs a frontend rebuild:"
put "# ./deploy-app.sh --frontend-only, NOT --skip-build."
[ -n "$FRONTEND_NOTE" ] && put "# $FRONTEND_NOTE"
if [ -n "${HAVE[REACT_APP_API_URL]:-}" ]; then
    emit REACT_APP_API_URL
else
    put "# REACT_APP_API_URL=   # frontend not inspected (--no-frontend)"
fi
blank

put "# ==========================="
put "# N8N CONFIGURATION"
put "# ==========================="
if [ -n "$N8N" ]; then
    emit N8N_USER
    emit N8N_PASSWORD
    emit N8N_WEBHOOK_URL
    emit TIMEZONE
else
    put "# No n8n container was read. n8n runs on its own host in this deployment;"
    put "# these only matter if you start the n8n service from this compose file."
    put "# N8N_USER=admin"
    put "# N8N_PASSWORD="
    put "# N8N_WEBHOOK_URL="
    put "# TIMEZONE=UTC"
fi

# --------------------------------------------------------------------------
# Read it back
# --------------------------------------------------------------------------
#
# Parse the file just written and check every value came back as it went in --
# proving the quoting round-trips rather than assuming it. This is deploy-app.sh's
# literal parse plus the unescaping Compose does inside double quotes, so what it
# compares is what Compose will hand the container.

unescape_dq() {
    # One left-to-right pass, so a literal backslash in the value cannot be
    # mistaken for the start of the escape that follows it.
    local s="$1" out="" c n
    while [ -n "$s" ]; do
        c="${s:0:1}"
        n="${s:1:1}"
        if [ "$c" = '\' ] && [ -n "$n" ]; then
            case "$n" in
                n)  out+=$'\n' ;;
                r)  out+=$'\r' ;;
                t)  out+=$'\t' ;;
                *)  out+="$n" ;;
            esac
            s="${s:2}"
        elif [ "$c" = '$' ] && [ "$n" = '$' ]; then
            out+='$'
            s="${s:2}"
        else
            out+="$c"
            s="${s:1}"
        fi
    done
    printf '%s' "$out"
}

env_get_from() {
    local file="$1" key="$2" line val found=0 sq="'" dq='"'
    val=""
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in ''|'#'*) continue ;; esac
        line="${line#export }"
        case "$line" in "$key"=*) ;; *) continue ;; esac
        val="${line#*=}"
        found=1
        case "$val" in
            "$dq"*"$dq")
                val="${val#$dq}"; val="${val%$dq}"
                val="$(unescape_dq "$val")"
                ;;
            "$sq"*"$sq") val="${val#$sq}"; val="${val%$sq}" ;;
        esac
    done < <(tr -d '\r' < "$file")
    [ "$found" -eq 1 ] && printf '%s' "$val"
    return 0
}

ROUNDTRIP_BAD=()
for k in "${ORDER[@]}"; do
    [ "${HAVE[$k]:-0}" = "1" ] || continue
    if [ "$(env_get_from "$TMP" "$k")" != "${VAL[$k]}" ]; then
        ROUNDTRIP_BAD+=("$k")
    fi
done

# --------------------------------------------------------------------------
# Hand it over
# --------------------------------------------------------------------------

if [ "$PRINT" -eq 1 ]; then
    cat "$TMP"
    DEST="(stdout)"
else
    if [ -e "$OUT" ]; then
        BAK="$OUT.bak.$(date '+%Y%m%d-%H%M%S')"
        cp -p "$OUT" "$BAK"
        say "${GREEN}OK${NC} Existing $OUT kept as $BAK"
    fi
    mv "$TMP" "$OUT"
    chmod 600 "$OUT"
    trap - EXIT
    DEST="$OUT"
fi

say ""
say "Recovered:"
for k in "${ORDER[@]}"; do
    if [ "${HAVE[$k]:-0}" = "1" ]; then
        printf '  %-22s %s\n' "$k" "$(mask "$k" "${VAL[$k]}")" >&2
    else
        printf '  %-22s %b\n' "$k" "${YELLOW}not found${NC}" >&2
    fi
done

# The app serves nothing without these, whatever else was recovered. CORS and
# the API URL are the usual casualties of a rebuild on a host whose address
# changed.
FATAL=()
for k in DATABASE_URL CORS_ORIGINS; do
    if [ "${HAVE[$k]:-0}" != "1" ] || [ -z "${VAL[$k]:-}" ]; then
        FATAL+=("$k")
    fi
done
if [ "$WANT_FRONTEND" -eq 1 ] && { [ "${HAVE[REACT_APP_API_URL]:-0}" != "1" ] || [ -z "${VAL[REACT_APP_API_URL]:-}" ]; }; then
    FATAL+=("REACT_APP_API_URL")
fi

# An LLM provider with no matching key gets past deploy-app.sh only by being
# wrong in .env too, so check the same pairing here.
PROVIDER="${VAL[LLM_PROVIDER]:-openai}"
case "$PROVIDER" in
    claude) [ -n "${VAL[ANTHROPIC_API_KEY]:-}" ] || FATAL+=("ANTHROPIC_API_KEY (LLM_PROVIDER=claude)") ;;
    openai) [ -n "${VAL[OPENAI_API_KEY]:-}" ]    || FATAL+=("OPENAI_API_KEY (LLM_PROVIDER=openai)") ;;
    gemini) [ -n "${VAL[GOOGLE_API_KEY]:-}" ]    || FATAL+=("GOOGLE_API_KEY (LLM_PROVIDER=gemini)") ;;
    *)      FATAL+=("LLM_PROVIDER='$PROVIDER' is not openai|claude|gemini") ;;
esac

say ""
if [ "${#QUOTED_ODD[@]}" -gt 0 ]; then
    say "${YELLOW}!${NC} Written double-quoted and escaped: ${QUOTED_ODD[*]}"
    say "    Those values contain a quote, a newline or a control character."
    say "    The read-back below covers them, but they are worth a look."
fi
if [ "${#ROUNDTRIP_BAD[@]}" -gt 0 ]; then
    say "${RED}X${NC} Did not survive a read-back: ${ROUNDTRIP_BAD[*]}"
    say "    Fix those lines by hand before deploying."
else
    say "${GREEN}OK${NC} Read back: every value parses to what the container has"
fi
if [ "${#MISSING[@]}" -gt 0 ]; then
    say "${YELLOW}!${NC} Left commented out: ${MISSING[*]}"
fi

if [ "${#FATAL[@]}" -gt 0 ]; then
    say "${RED}X${NC} Written to $DEST, but incomplete:"
    for f in "${FATAL[@]}"; do say "      $f"; done
    say ""
    say "    Fill these in before ./deploy-app.sh -- it validates the same things"
    say "    and will refuse the deploy otherwise."
    exit 1
fi

say "${GREEN}OK${NC} Written to $DEST"
say ""
say "Next:"
say "  ./deploy-app.sh --skip-build      # config-only change, no rebuild"
say "  ./deploy-app.sh --frontend-only   # only if REACT_APP_API_URL changed"
say ""
