#!/bin/bash
# =============================================================================
# College Management System – Deployment Script
# Deploys the Flask application to EC2 via SSH/SCP
# Usage:
#   export EC2_HOST=<public-ip>
#   export EC2_KEY_PATH=~/.ssh/your-key.pem
#   export DB_HOST=<rds-endpoint>
#   export DB_PASSWORD=<db-password>
#   export S3_BUCKET=<bucket-name>
#   export SECRET_KEY=<flask-secret-key>
#   export ADMIN_EMAIL=<admin@example.com>
#   export ADMIN_PASSWORD=<admin-password>
#   bash scripts/deploy.sh
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()    { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; }

die() { log_error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Check required environment variables
# ---------------------------------------------------------------------------
log_step "Checking required environment variables"

REQUIRED_VARS=(
  EC2_HOST
  EC2_KEY_PATH
  DB_HOST
  DB_PASSWORD
  S3_BUCKET
  SECRET_KEY
  ADMIN_EMAIL
  ADMIN_PASSWORD
)

MISSING=()
for VAR in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!VAR:-}" ]]; then
    MISSING+=("$VAR")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  log_error "The following required environment variables are not set:"
  for VAR in "${MISSING[@]}"; do
    echo -e "  ${RED}✗${NC} $VAR"
  done
  die "Set all required variables and re-run."
fi

log_success "All required environment variables are set."

# Derived / optional variables with defaults
DB_USERNAME="${DB_USERNAME:-college_admin}"
DB_NAME="${DB_NAME:-college_management}"
DB_PORT="${DB_PORT:-3306}"
APP_ENV="${APP_ENV:-production}"
APP_DIR="/opt/college-app"
SSH_OPTS="-i ${EC2_KEY_PATH} -o StrictHostKeyChecking=no -o ConnectTimeout=30"
SSH_CMD="ssh ${SSH_OPTS} ubuntu@${EC2_HOST}"
SCP_CMD="scp ${SSH_OPTS}"

# Determine project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo ""
echo -e "${BOLD}Deployment Configuration:${NC}"
echo -e "  EC2 Host  : ${CYAN}${EC2_HOST}${NC}"
echo -e "  DB Host   : ${CYAN}${DB_HOST}${NC}"
echo -e "  S3 Bucket : ${CYAN}${S3_BUCKET}${NC}"
echo -e "  App Dir   : ${CYAN}${APP_DIR}${NC}"
echo -e "  Environment: ${CYAN}${APP_ENV}${NC}"
echo ""

# ---------------------------------------------------------------------------
# 2. Wait for EC2 to be reachable
# ---------------------------------------------------------------------------
log_step "Checking EC2 connectivity"

MAX_RETRIES=10
for i in $(seq 1 $MAX_RETRIES); do
  if ssh ${SSH_OPTS} ubuntu@"${EC2_HOST}" "echo ok" &>/dev/null; then
    log_success "EC2 is reachable."
    break
  fi
  if [[ $i -eq $MAX_RETRIES ]]; then
    die "Cannot reach EC2 after ${MAX_RETRIES} attempts."
  fi
  log_warn "Attempt $i/$MAX_RETRIES – waiting 10 s..."
  sleep 10
done

# ---------------------------------------------------------------------------
# 3. Wait for bootstrap to complete
# ---------------------------------------------------------------------------
log_step "Waiting for EC2 bootstrap to complete"

BOOTSTRAP_MAX=60   # max 5 minutes (60 × 5 s)
for i in $(seq 1 $BOOTSTRAP_MAX); do
  if $SSH_CMD "test -f /var/log/bootstrap-complete.log" &>/dev/null; then
    log_success "Bootstrap complete."
    break
  fi
  if [[ $i -eq $BOOTSTRAP_MAX ]]; then
    die "Bootstrap did not complete within the timeout window."
  fi
  log_warn "Waiting for bootstrap… ($((i * 5))s elapsed)"
  sleep 5
done

# ---------------------------------------------------------------------------
# 4. Sync application code to EC2
# ---------------------------------------------------------------------------
log_step "Syncing application code to EC2"

rsync -avz --delete \
  -e "ssh ${SSH_OPTS}" \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.terraform' \
  --exclude='terraform.tfvars' \
  --exclude='node_modules' \
  --exclude='.DS_Store' \
  "${PROJECT_ROOT}/" \
  "ubuntu@${EC2_HOST}:${APP_DIR}/"

log_success "Code synced successfully."

# ---------------------------------------------------------------------------
# 5. Install Python dependencies
# ---------------------------------------------------------------------------
log_step "Installing Python dependencies"

$SSH_CMD bash <<REMOTE
  set -e
  source ${APP_DIR}/venv/bin/activate
  pip install --upgrade pip
  pip install -r ${APP_DIR}/backend/requirements.txt
REMOTE

log_success "Python dependencies installed."

# ---------------------------------------------------------------------------
# 6. Write .env file on EC2
# ---------------------------------------------------------------------------
log_step "Writing .env configuration file"

$SSH_CMD bash <<REMOTE
  set -e
  cat > ${APP_DIR}/.env <<EOF
# College Management System – Environment Configuration
# Generated by deploy.sh on \$(date -u '+%Y-%m-%d %H:%M:%S UTC')
# DO NOT COMMIT THIS FILE

FLASK_ENV=${APP_ENV}
FLASK_DEBUG=0
SECRET_KEY=${SECRET_KEY}

# Database
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USERNAME=${DB_USERNAME}
DB_PASSWORD=${DB_PASSWORD}
DATABASE_URL=mysql+pymysql://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# AWS
AWS_DEFAULT_REGION=ap-south-1
S3_BUCKET=${S3_BUCKET}

# Admin seed account
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
MAX_CONTENT_LENGTH=52428800
EOF
  chmod 600 ${APP_DIR}/.env
  chown appuser:appuser ${APP_DIR}/.env
REMOTE

log_success ".env file written and secured."

# ---------------------------------------------------------------------------
# 7. Run Flask database migrations
# ---------------------------------------------------------------------------
log_step "Running Flask database migrations"

$SSH_CMD bash <<REMOTE
  set -e
  source ${APP_DIR}/venv/bin/activate
  export \$(grep -v '^#' ${APP_DIR}/.env | xargs)
  cd ${APP_DIR}/backend
  flask db init 2>/dev/null || true
  flask db migrate -m "Initial migration" 2>/dev/null || true
  flask db upgrade
REMOTE

log_success "Database migrations applied."

# ---------------------------------------------------------------------------
# 8. Seed database (roles, permissions, initial admin)
# ---------------------------------------------------------------------------
log_step "Seeding database"

$SSH_CMD bash <<REMOTE
  set -e
  source ${APP_DIR}/venv/bin/activate
  export \$(grep -v '^#' ${APP_DIR}/.env | xargs)
  cd ${APP_DIR}/backend
  python database.py
REMOTE

log_success "Database seeded."

# ---------------------------------------------------------------------------
# 9. Configure and start systemd service
# ---------------------------------------------------------------------------
log_step "Configuring systemd service"

$SSH_CMD bash <<REMOTE
  set -e
  # Create log directory
  mkdir -p /var/log/college-app
  chown appuser:appuser /var/log/college-app

  # Copy service file
  cp ${APP_DIR}/config/college-management.service /etc/systemd/system/college-management.service
  chmod 644 /etc/systemd/system/college-management.service

  # Reload daemon and enable
  systemctl daemon-reload
  systemctl enable college-management
  systemctl restart college-management
REMOTE

log_success "Systemd service started."

# ---------------------------------------------------------------------------
# 10. Configure Nginx
# ---------------------------------------------------------------------------
log_step "Configuring Nginx"

$SSH_CMD bash <<REMOTE
  set -e
  cp ${APP_DIR}/config/nginx.conf /etc/nginx/sites-available/college-management
  ln -sf /etc/nginx/sites-available/college-management /etc/nginx/sites-enabled/college-management
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl reload nginx
REMOTE

log_success "Nginx configured and reloaded."

# ---------------------------------------------------------------------------
# 11. Verify deployment
# ---------------------------------------------------------------------------
log_step "Verifying deployment"

sleep 8
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "http://${EC2_HOST}/health" || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
  log_success "Health check passed (HTTP ${HTTP_CODE})."
else
  log_warn "Health check returned HTTP ${HTTP_CODE}. Check application logs."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   Deployment SUCCESSFUL                          ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Application URL :${NC} http://${EC2_HOST}"
echo -e "  ${BOLD}EC2 SSH         :${NC} ssh -i ${EC2_KEY_PATH} ubuntu@${EC2_HOST}"
echo -e "  ${BOLD}App Logs        :${NC} journalctl -u college-management -f"
echo -e "  ${BOLD}Nginx Logs      :${NC} tail -f /var/log/nginx/error.log"
echo ""
