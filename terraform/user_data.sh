#!/bin/bash
# =============================================================================
# College Management System – EC2 User Data Bootstrap Script
# OS: Ubuntu 24.04 LTS
# Runs once at first boot to prepare the server for application deployment.
# =============================================================================
set -e
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

echo "=========================================="
echo " College Management System – EC2 Bootstrap"
echo " $(date '+%Y-%m-%d %H:%M:%S UTC')"
echo "=========================================="

# ---------------------------------------------------------------------------
# 1. System update & upgrade
# ---------------------------------------------------------------------------
echo "[1/9] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -yq \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold"

# ---------------------------------------------------------------------------
# 2. Install system dependencies
# ---------------------------------------------------------------------------
echo "[2/9] Installing system dependencies..."
apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  python3-setuptools \
  nginx \
  git \
  curl \
  wget \
  unzip \
  build-essential \
  libmysqlclient-dev \
  pkg-config \
  libssl-dev \
  libffi-dev \
  default-libmysqlclient-dev \
  ufw \
  fail2ban \
  logrotate \
  htop \
  vim \
  jq

# ---------------------------------------------------------------------------
# 3. Upgrade pip to latest
# ---------------------------------------------------------------------------
echo "[3/9] Upgrading pip..."
python3 -m pip install --upgrade pip --break-system-packages

# ---------------------------------------------------------------------------
# 4. Create application user (non-login system user)
# ---------------------------------------------------------------------------
echo "[4/9] Creating application user 'appuser'..."
if ! id -u appuser &>/dev/null; then
  useradd -r -s /bin/bash -m -d /opt/college-app appuser
fi

# ---------------------------------------------------------------------------
# 5. Create application directory structure
# ---------------------------------------------------------------------------
echo "[5/9] Setting up application directories..."
mkdir -p /opt/college-app
mkdir -p /var/log/college-app
chown appuser:appuser /opt/college-app
chown appuser:appuser /var/log/college-app
chmod 755 /opt/college-app

# ---------------------------------------------------------------------------
# 6. Create Python virtual environment
# ---------------------------------------------------------------------------
echo "[6/9] Creating Python virtual environment..."
sudo -u appuser python3 -m venv /opt/college-app/venv
/opt/college-app/venv/bin/pip install --upgrade pip setuptools wheel

# ---------------------------------------------------------------------------
# 7. Basic Nginx configuration (placeholder – overridden by deploy.sh)
# ---------------------------------------------------------------------------
echo "[7/9] Configuring Nginx..."
# Disable default site
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
nginx -t && systemctl enable nginx && systemctl start nginx

# ---------------------------------------------------------------------------
# 8. Configure UFW firewall
# ---------------------------------------------------------------------------
echo "[8/9] Configuring UFW firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment 'SSH'
ufw allow 80/tcp    comment 'HTTP'
ufw allow 443/tcp   comment 'HTTPS'
ufw --force enable

# ---------------------------------------------------------------------------
# 9. Configure fail2ban for SSH protection
# ---------------------------------------------------------------------------
echo "[9/9] Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
backend = %(syslog_backend)s
EOF

systemctl enable fail2ban
systemctl start fail2ban

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo " Bootstrap COMPLETE – $(date '+%Y-%m-%d %H:%M:%S UTC')"
echo " Server is ready for application deployment"
echo "=========================================="
echo "EC2 bootstrap complete" > /var/log/bootstrap-complete.log
