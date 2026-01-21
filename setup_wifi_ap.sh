#!/bin/bash

# PhotoBooth WiFi Access Point Setup Script
# This script configures a Raspberry Pi to act as a WiFi Access Point with captive portal support for photo downloads

set -e

echo "=================================="
echo "PhotoBooth WiFi AP Setup"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "-- Installing required packages..."
apt-get update
apt-get install -y hostapd dnsmasq iptables-persistent

# Stop services during configuration
echo "⏸-- Stopping services..."
systemctl stop hostapd
systemctl stop dnsmasq

# Backup original configuration files
echo "-- Backing up original configurations..."
cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup 2>/dev/null || true
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup 2>/dev/null || true
cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup 2>/dev/null || true

# Configure static IP for wlan0
echo "-- Configuring static IP for wlan0..."
cat >> /etc/dhcpcd.conf << EOF

# PhotoBooth WiFi AP Configuration
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF

# Configure dnsmasq (DHCP and DNS server)
echo "-- Configuring dnsmasq..."
cat > /etc/dnsmasq.conf << EOF
# PhotoBooth WiFi AP - DHCP Configuration
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.100,255.255.255.0,24h
domain=photobooth.local
address=/#/192.168.4.1

# Captive Portal - Redirect all DNS queries to AP
address=/captive.apple.com/192.168.4.1
address=/connectivitycheck.gstatic.com/192.168.4.1
address=/www.msftconnecttest.com/192.168.4.1
address=/detectportal.firefox.com/192.168.4.1

# Logging (optional, comment out for production)
log-queries
log-dhcp
EOF

# Configure hostapd (WiFi Access Point)
echo "-- Configuring hostapd..."
cat > /etc/hostapd/hostapd.conf << EOF
# PhotoBooth WiFi AP Configuration
interface=wlan0
driver=nl80211

# Network name (SSID)
ssid=PhotoBooth

# WiFi channel (1-13)
channel=6

# WiFi mode (a=5GHz, g=2.4GHz)
hw_mode=g

# 802.11n support
ieee80211n=1

# No password (open network)
# For password protection, uncomment and configure:
# wpa=2
# wpa_passphrase=YOUR_PASSWORD_HERE
# wpa_key_mgmt=WPA-PSK
# wpa_pairwise=TKIP
# rsn_pairwise=CCMP

# Country code (adjust for your location)
country_code=FR

# Beacon interval
beacon_int=100

# DTIM period
dtim_period=2
EOF

# Tell hostapd where to find the config file
echo "-- Updating hostapd daemon configuration..."
cat > /etc/default/hostapd << EOF
# Defaults for hostapd initscript
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF

# Enable IP forwarding (for internet sharing if needed via eth0)
echo "-- Enabling IP forwarding..."
sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1

# Configure iptables for NAT (if you want to share internet via eth0)
echo "-- Configuring iptables..."
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT

# Save iptables rules
netfilter-persistent save

# Unmask and enable services
echo "-- Enabling services..."
systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq

# Start services
echo "-- Starting services..."
systemctl start hostapd
systemctl start dnsmasq

# Restart dhcpcd
systemctl restart dhcpcd

echo ""
echo "================================="
echo "WiFi Access Point Setup Complete!"
echo "================================="
echo ""
echo "Network Details:"
echo "   SSID: PhotoBooth"
echo "   IP Address: 192.168.4.1"
echo "   DHCP Range: 192.168.4.10 - 192.168.4.100"
echo "   Security: Open (No password)"
echo ""
echo "Web Server will be available at:"
echo "   http://192.168.4.1:5000"
echo ""
echo "To connect:"
echo "   1. Scan QR code displayed on photobooth"
echo "   2. Connect to 'PhotoBooth' WiFi network"
echo "   3. Browser will auto-open to download page"
echo ""
echo "Service Status:"
systemctl status hostapd --no-pager | head -n 3
systemctl status dnsmasq --no-pager | head -n 3
echo ""
echo "Please reboot for all changes to take effect:"
echo "   sudo reboot"
echo ""
