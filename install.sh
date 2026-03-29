#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/piknock"
SERVICE_FILE="/etc/systemd/system/piknock.service"

info()  { echo -e "${CYAN}[PiKnock]${NC} $1"; }
ok()    { echo -e "${GREEN}[PiKnock]${NC} $1"; }
err()   { echo -e "${RED}[PiKnock]${NC} $1"; }

# -------------------------------------------------------------------
# Checks
# -------------------------------------------------------------------

if [ "$EUID" -ne 0 ]; then
    err "Please run with sudo: sudo ./install.sh"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$(whoami)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

info "Installing PiKnock for user: $ACTUAL_USER"

# -------------------------------------------------------------------
# 1. Install dependencies
# -------------------------------------------------------------------

info "Installing wakeonlan..."
apt-get update -qq
apt-get install -y -qq wakeonlan
ok "wakeonlan installed"

# -------------------------------------------------------------------
# 2. Deploy files
# -------------------------------------------------------------------

info "Deploying to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/piknock.py" "$INSTALL_DIR/"

if [ ! -f "$INSTALL_DIR/config.json" ]; then
    cp "$SCRIPT_DIR/config.example.json" "$INSTALL_DIR/config.json"
    info "Created config.json from example template"
else
    info "Existing config.json preserved"
fi

chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$INSTALL_DIR"
ok "Files deployed"

# -------------------------------------------------------------------
# 3. Install systemd service
# -------------------------------------------------------------------

info "Installing systemd service..."
sed "s/__USER__/$ACTUAL_USER/g" "$SCRIPT_DIR/piknock.service" > "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable piknock
systemctl restart piknock
ok "Service installed and started"

# -------------------------------------------------------------------
# 4. Optional: Direct Ethernet setup
# -------------------------------------------------------------------

echo ""
read -p "$(echo -e "${CYAN}[PiKnock]${NC} Do you have a direct Ethernet cable to a target PC? [y/N] ")" -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    ETH_IFACE="${ETH_IFACE:-eth0}"
    ETH_IP="${ETH_IP:-10.0.0.1}"
    ETH_MASK="24"

    info "Configuring $ETH_IFACE with static IP $ETH_IP/$ETH_MASK..."

    # Detect network manager
    if systemctl is-active --quiet NetworkManager; then
        info "Detected: NetworkManager"
        nmcli con add type ethernet con-name "piknock-direct" ifname "$ETH_IFACE" \
            ipv4.method manual ipv4.addresses "$ETH_IP/$ETH_MASK" 2>/dev/null || \
        nmcli con modify "piknock-direct" ipv4.method manual ipv4.addresses "$ETH_IP/$ETH_MASK"
        nmcli con up "piknock-direct"
    elif systemctl is-active --quiet dhcpcd; then
        info "Detected: dhcpcd"
        if ! grep -q "interface $ETH_IFACE" /etc/dhcpcd.conf 2>/dev/null; then
            cat >> /etc/dhcpcd.conf <<EOF

# PiKnock - Direct Ethernet connection
interface $ETH_IFACE
static ip_address=$ETH_IP/$ETH_MASK
nogateway
EOF
            systemctl restart dhcpcd
        else
            info "$ETH_IFACE already configured in dhcpcd.conf"
        fi
    else
        err "Could not detect NetworkManager or dhcpcd. Configure $ETH_IFACE manually with IP $ETH_IP/$ETH_MASK"
    fi

    ok "Direct Ethernet configured"
    echo ""
    info "On the target PC, set the Ethernet interface to:"
    info "  IP: 10.0.0.2  Subnet: 255.255.255.0  No gateway"
    info "  Then add a device in PiKnock with broadcast: 10.0.0.255"
fi

# -------------------------------------------------------------------
# Done
# -------------------------------------------------------------------

echo ""
LOCAL_IP=$(hostname -I | awk '{print $1}')
ok "============================================"
ok "  PiKnock is running!"
ok "  http://${LOCAL_IP}:8080"
ok "============================================"
echo ""
info "Logs: journalctl -u piknock -f"
info "Config: $INSTALL_DIR/config.json"
