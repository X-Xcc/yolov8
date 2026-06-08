#!/bin/bash
set -e

# ============================================================
# YOLOv8 Security - Server Deployment Script
# ============================================================
# Usage:
#   1. Run build.bat on Windows to generate deploy-pkg/
#   2. Upload deploy-pkg/* to server:/opt/yolov8-security/
#   3. Run this script on the server:
#      cd /opt/yolov8-security && bash deploy/deploy.sh
# ============================================================

APP_NAME="yolov8-security"
APP_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}"
JAVA_MIN_VERSION=17

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
# Step 1: Check Java
# ============================================================
check_java() {
    log_info "Checking Java installation..."
    if command -v java &>/dev/null; then
        JAVA_VER=$(java -version 2>&1 | head -1 | grep -oP '"\K[0-9]+' || echo "0")
        if [ "$JAVA_VER" -ge "$JAVA_MIN_VERSION" ]; then
            log_info "Java ${JAVA_VER} found"
            return 0
        else
            log_warn "Java ${JAVA_VER} is too old (need ${JAVA_MIN_VERSION}+)"
        fi
    else
        log_warn "Java not found"
    fi

    log_info "Installing JDK (trying package manager)..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq openjdk-17-jdk && return 0
    fi
    if command -v yum &>/dev/null; then
        yum install -y -q java-17-openjdk-devel && return 0
    fi

    # Fallback: manual download
    log_warn "Package install failed. Downloading JDK 17 manually..."
    JDK_DIR="/opt/jdk-17"
    if [ ! -d "$JDK_DIR" ]; then
        cd /tmp
        wget -q "https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_linux-x64_bin.tar.gz" -O jdk17.tar.gz
        mkdir -p "$JDK_DIR"
        tar -xzf jdk17.tar.gz -C "$JDK_DIR" --strip-components=1
        rm -f jdk17.tar.gz
    fi
    # Create symlink
    ln -sf "$JDK_DIR/bin/java" /usr/local/bin/java
    log_info "JDK 17 installed to ${JDK_DIR}"

    # Verify
    if ! command -v java &>/dev/null; then
        log_error "Java installation failed"
        exit 1
    fi
    JAVA_VER=$(java -version 2>&1 | head -1 | grep -oP '"\K[0-9]+')
    log_info "Java ${JAVA_VER} installed successfully"
}

# ============================================================
# Step 2: Create directories
# ============================================================
setup_directories() {
    log_info "Setting up directories..."
    mkdir -p "${APP_DIR}/data/detections"
    mkdir -p "${APP_DIR}/data/frames"
    mkdir -p "${APP_DIR}/data/db"
    mkdir -p "${APP_DIR}/logs"
    mkdir -p "${APP_DIR}/web/dist"

    # Empty data dir for port 5001 (zero-data instance)
    mkdir -p "${APP_DIR}/data-empty/detections"
    mkdir -p "${APP_DIR}/data-empty/frames"
    mkdir -p "${APP_DIR}/data-empty/db"
    log_info "Created data-empty directories for port 5001"

    # Create empty cameras.json if not present
    if [ ! -f "${APP_DIR}/detection/cameras.json" ]; then
        mkdir -p "${APP_DIR}/detection"
        echo '[]' > "${APP_DIR}/detection/cameras.json"
        log_info "Created empty detection/cameras.json"
    fi
}

# ============================================================
# Step 3: Configure environment
# ============================================================
setup_env() {
    log_info "Configuring environment..."
    ENV_FILE="${APP_DIR}/.env"

    if [ ! -f "$ENV_FILE" ]; then
        log_warn ".env not found, creating from template..."
        cat > "$ENV_FILE" << 'ENVEOF'
API_KEY=
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
JWT_SECRET=changeme-to-a-random-string-at-least-32-chars-long!!
ENVEOF
        log_warn ">>> IMPORTANT: Edit ${ENV_FILE} with your credentials! <<<"
    fi

    # Validate JWT_SECRET length
    JWT_LEN=$(grep -oP '^JWT_SECRET=\K.*' "$ENV_FILE" 2>/dev/null | wc -c)
    if [ "$JWT_LEN" -lt 33 ]; then
        log_warn "JWT_SECRET is too short (< 32 chars). Generating a random one..."
        RANDOM_SECRET=$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 48)
        sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${RANDOM_SECRET}|" "$ENV_FILE"
        log_info "JWT_SECRET updated"
    fi
}

# ============================================================
# Step 4: Remove Nginx on port 80
# ============================================================
stop_nginx() {
    log_info "Removing Nginx on port 80..."
    if systemctl is-active --quiet nginx 2>/dev/null; then
        systemctl stop nginx 2>/dev/null
        systemctl disable nginx 2>/dev/null
        log_info "Nginx stopped and disabled"
    else
        log_info "Nginx not running, skip"
    fi
    # Also kill anything on port 80
    if command -v fuser &>/dev/null; then
        fuser -k 80/tcp 2>/dev/null || true
    fi
}

# ============================================================
# Step 5: Create systemd service
# ============================================================
setup_service() {
    log_info "Creating systemd service..."

    WAR_FILE="${APP_DIR}/app.war"
    if [ ! -f "$WAR_FILE" ]; then
        log_error "app.war not found at ${WAR_FILE}"
        log_error "Please upload the deploy-pkg/ contents first."
        exit 1
    fi

    # Detect Java path
    JAVA_BIN=$(command -v java)
    if [ -z "$JAVA_BIN" ]; then
        log_error "Java not found in PATH"
        exit 1
    fi
    log_info "Using Java: ${JAVA_BIN}"

    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << SVCEOF
[Unit]
Description=YOLOv8 Security Monitor
After=network.target

[Service]
Type=simple
User=yolov8
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${JAVA_BIN} -Xms256m -Xmx1024m -jar ${WAR_FILE} --server.port=5000
Restart=on-failure
RestartSec=10
StandardOutput=append:${APP_DIR}/logs/app.log
StandardError=append:${APP_DIR}/logs/app.log

NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${APP_DIR}/data ${APP_DIR}/logs ${APP_DIR}/detection

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    log_info "Systemd service created and enabled"

    # Second instance on port 5001 — empty data, all pages show zero
    ANALYSIS_SERVICE="${SERVICE_NAME}-analysis"
    cat > "/etc/systemd/system/${ANALYSIS_SERVICE}.service" << SVCEOF
[Unit]
Description=YOLOv8 Security Monitor - Zero-Data Panel (Port 5001)
After=network.target

[Service]
Type=simple
User=yolov8
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DATA_DIR=./data-empty
ExecStart=${JAVA_BIN} -Xms256m -Xmx512m -jar ${WAR_FILE} --server.port=5001
Restart=on-failure
RestartSec=10
StandardOutput=append:${APP_DIR}/logs/app-5001.log
StandardError=append:${APP_DIR}/logs/app-5001.log

NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${APP_DIR}/data-empty ${APP_DIR}/logs ${APP_DIR}/detection

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl enable "${ANALYSIS_SERVICE}"
    log_info "Zero-data panel service created and enabled (port 5001)"
}

# ============================================================
# Step 6: Firewall
# ============================================================
setup_firewall() {
    log_info "Configuring firewall (ports 5000, 5001)..."
    if command -v ufw &>/dev/null; then
        ufw allow 5000/tcp 2>/dev/null && log_info "ufw: allowed port 5000"
        ufw allow 5001/tcp 2>/dev/null && log_info "ufw: allowed port 5001"
    elif command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=5000/tcp 2>/dev/null
        firewall-cmd --permanent --add-port=5001/tcp 2>/dev/null
        firewall-cmd --reload 2>/dev/null && log_info "firewalld: allowed ports 5000, 5001"
    else
        log_warn "No firewall tool found. Make sure ports 5000, 5001 are open in Alibaba Cloud security group!"
    fi
}

# ============================================================
# Step 7: Start service
# ============================================================
start_service() {
    log_info "Starting ${SERVICE_NAME}..."
    systemctl restart "${SERVICE_NAME}"
    sleep 3

    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_info "Main service (port 5000) is running!"
    else
        log_error "Service failed to start. Check logs:"
        log_error "  journalctl -u ${SERVICE_NAME} -n 50"
        log_error "  cat ${APP_DIR}/logs/app.log"
        exit 1
    fi

    log_info "Starting ${SERVICE_NAME}-analysis (port 5001)..."
    systemctl restart "${SERVICE_NAME}-analysis"
    sleep 3

    if systemctl is-active --quiet "${SERVICE_NAME}-analysis"; then
        log_info "Analysis service (port 5001) is running!"
    else
        log_error "Analysis service failed to start. Check logs:"
        log_error "  journalctl -u ${SERVICE_NAME}-analysis -n 50"
        log_error "  cat ${APP_DIR}/logs/app-5001.log"
        exit 1
    fi
}

# ============================================================
# Main
# ============================================================
main() {
    echo "========================================"
    echo "  YOLOv8 Security - Server Deployment"
    echo "========================================"
    echo ""

    check_java
    setup_directories
    setup_env
    stop_nginx
    setup_service
    setup_firewall
    start_service

    echo ""
    echo "========================================"
    echo "  Deployment Complete!"
    echo "========================================"
    echo ""
    echo "  :5000 → 完整应用（前端 mock 假数据）"
    echo "  :5001 → 完整应用（数据全零）"
    echo "  Logs:     tail -f ${APP_DIR}/logs/app.log"
    echo "  Logs(5001): tail -f ${APP_DIR}/logs/app-5001.log"
    echo "  Ctrl:     systemctl status ${SERVICE_NAME}"
    echo ""
    echo "  Login with credentials from ${APP_DIR}/.env"
    echo ""
}

main "$@"
