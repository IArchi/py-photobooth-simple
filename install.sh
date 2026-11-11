#!/bin/bash

# Simple PhotoBooth - Automated Installation Script
# This script will guide you through the installation process

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PHOTOBOOTH_PYTHON="$VENV_DIR/bin/python"
NEED_REBOOT=false
SKIP_ONLINE_STEPS=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

append_root_line_if_missing() {
    local file="$1"
    local line="$2"

    sudo touch "$file"
    if sudo grep -Fqx "$line" "$file"; then
        return 0
    fi

    printf '%s\n' "$line" | sudo tee -a "$file" > /dev/null
}

append_root_block_if_missing() {
    local file="$1"
    local marker="$2"
    local block="$3"

    sudo touch "$file"
    if sudo grep -Fqx "$marker" "$file"; then
        return 0
    fi

    printf '\n%s\n%s\n' "$marker" "$block" | sudo tee -a "$file" > /dev/null
}

backup_root_file_once() {
    local source="$1"
    local backup_path="${2:-$1.backup}"

    if ! sudo test -e "$source"; then
        return 0
    fi

    if sudo test -e "$backup_path"; then
        return 0
    fi

    sudo cp "$source" "$backup_path"
}

write_root_file_if_changed() {
    local path="$1"
    local content="$2"
    local mode="${3:-644}"
    local temp_file
    temp_file=$(mktemp)

    printf '%s' "$content" > "$temp_file"

    if sudo test -f "$path" && sudo cmp -s "$temp_file" "$path"; then
        rm -f "$temp_file"
        return 0
    fi

    sudo install -d "$(dirname "$path")"
    sudo install -m "$mode" "$temp_file" "$path"
    rm -f "$temp_file"
}

replace_or_append_root_line() {
    local file="$1"
    local search_pattern="$2"
    local replacement_line="$3"
    local temp_file
    temp_file=$(mktemp)

    sudo touch "$file"

    if sudo grep -Eq "$search_pattern" "$file"; then
        sudo sed -E "s|$search_pattern|$replacement_line|" "$file" > "$temp_file"
    else
        sudo cp "$file" "$temp_file"
        printf '\n%s\n' "$replacement_line" >> "$temp_file"
    fi

    if sudo cmp -s "$temp_file" "$file"; then
        rm -f "$temp_file"
        return 0
    fi

    sudo install -m 644 "$temp_file" "$file"
    rm -f "$temp_file"
}

# Ask yes/no question
ask_yes_no() {
    while true; do
        if ! read -r -p "$1 (y/n): " yn; then
            print_error "Input closed; installation stopped"
            exit 1
        fi
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes (y) or no (n).";;
        esac
    done
}

# Check if running on Raspberry Pi
is_raspberry_pi() {
    if [ -f /proc/device-tree/model ]; then
        grep -q "Raspberry Pi" /proc/device-tree/model
        return $?
    fi
    return 1
}

escape_systemd_value() {
    printf '%s' "$1" | sed 's/[[:space:]]/\\x20/g'
}

get_wifi_country() {
    local country=""

    if command -v raspi-config >/dev/null 2>&1; then
        country=$(raspi-config nonint get_wifi_country 2>/dev/null || true)
    fi

    if [[ ! "$country" =~ ^[A-Za-z]{2}$ ]] && command -v iw >/dev/null 2>&1; then
        country=$(iw reg get 2>/dev/null | sed -n 's/^country \([A-Za-z][A-Za-z]\):.*/\1/p' | sed -n '1p')
    fi

    if [[ ! "$country" =~ ^[A-Za-z]{2}$ ]]; then
        country=$(locale 2>/dev/null | sed -n 's/^LANG=[^_]*_\([A-Za-z][A-Za-z]\).*/\1/p')
    fi

    if [[ "$country" =~ ^[A-Za-z]{2}$ ]]; then
        printf '%s' "${country^^}"
    else
        return 1
    fi
}

has_internet_connection() {
    if command_exists curl; then
        curl -fsI --connect-timeout 5 --max-time 10 https://deb.debian.org >/dev/null 2>&1 && return 0
    fi

    if command_exists wget; then
        wget -q --spider --timeout=10 https://deb.debian.org >/dev/null 2>&1 && return 0
    fi

    ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1
}

# Banner
cd "$SCRIPT_DIR"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║         Simple PhotoBooth Installation Script        ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root or with sudo"
    print_info "The script will ask for sudo password when needed"
    exit 1
fi

# Welcome message
print_info "This script will help you install and configure the Simple PhotoBooth application"
print_info "You will be asked which components you want to install"
echo ""

if ! ask_yes_no "Do you want to continue with the installation?"; then
    print_info "Installation cancelled"
    exit 0
fi

echo ""
print_info "Starting installation..."
echo ""

if ! has_internet_connection; then
    print_warning "No Internet connection detected. Network downloads and package installations will be skipped."
    if ask_yes_no "Do you want to continue anyway?"; then
        SKIP_ONLINE_STEPS=true
    else
        print_info "Installation cancelled"
        exit 0
    fi
    echo ""
fi

# ============================================================================
# STEP 1: Base System Dependencies
# ============================================================================
print_info "Step 1/9: Installing base system dependencies..."

if [ "$SKIP_ONLINE_STEPS" = true ]; then
    print_warning "Skipping base dependencies installation because Internet is unavailable"
else
    sudo apt-get update
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y gcc make build-essential git scons swig ffmpeg libturbojpeg0 python3-pip python3-venv python3-numpy libgl1 libgphoto2-dev

    print_success "Base dependencies installed"
fi
echo ""

# ============================================================================
# STEP 2: Python Dependencies
# ============================================================================
print_info "Step 2/9: Preparing the project virtual environment..."

# Use the distribution Python so APT's libcamera and CUPS bindings share its ABI.
# Re-running venv also enables system packages in an existing isolated environment.
/usr/bin/python3 -m venv --system-site-packages "$VENV_DIR"

if [ "$SKIP_ONLINE_STEPS" = true ]; then
    print_warning "Skipping Python dependencies installation because Internet is unavailable"
else
    # Keep APT's NumPy ABI for native camera extensions. An incompatible OpenCV
    # release must be resolved to an older compatible version, not upgrade NumPy.
    SYSTEM_NUMPY_VERSION=$(/usr/bin/python3 -c 'import numpy; print(numpy.__version__)')
    "$PHOTOBOOTH_PYTHON" -m pip install "numpy==$SYSTEM_NUMPY_VERSION" -r "$SCRIPT_DIR/requirements.txt"
    "$PHOTOBOOTH_PYTHON" -c 'import numpy, cv2, kivy, lxml.etree, psutil, flask, qrcode, PIL; print("Application dependency imports OK")'
    "$PHOTOBOOTH_PYTHON" -m pip check

    print_success "Python dependencies installed in $VENV_DIR"
fi
echo ""

# ============================================================================
# STEP 3: Kiosk Mode (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 3/9: Do you want to enable Kiosk Mode (hide mouse, taskbar, etc.)?"; then
        print_info "Configuring Kiosk Mode..."
        
        if [ -f /etc/wayfire/defaults.ini ]; then
            backup_root_file_once /etc/wayfire/defaults.ini
            # Hide mouse and panel
            if ! sudo grep -Eq '^[[:space:]]*background[[:space:]]*=[[:space:]]*wf-background[[:space:]]*$' /etc/wayfire/defaults.ini; then
                sudo sed -i '/^\[autostart\]$/a background = wf-background' /etc/wayfire/defaults.ini
            fi

            # Hide taskbar
            sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini
        else
            print_warning "/etc/wayfire/defaults.ini not found; skipping Wayfire kiosk tweaks"
        fi
        
        # Disable power warning
        append_root_line_if_missing /boot/firmware/config.txt "avoid_warnings=1"
        sudo apt remove lxplug-ptbatt -y || true
        
        # Disable media mount dialog
        backup_root_file_once /etc/xdg/pcmanfm/LXDE-pi/pcmanfm.conf
        backup_root_file_once /etc/xdg/pcmanfm/default/pcmanfm.conf
        sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/LXDE-pi/pcmanfm.conf || true
        sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/default/pcmanfm.conf || true
        
        print_success "Kiosk Mode configured"
        NEED_REBOOT=true
    else
        print_info "Skipping Kiosk Mode configuration"
    fi
else
    print_info "Step 3/9: Kiosk Mode (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 4: Ingcool 7" Touchscreen (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 4/9: Are you using the Ingcool 7\" touchscreen?"; then
        print_info "Configuring Ingcool 7\" touchscreen..."
        
        append_root_block_if_missing /boot/firmware/config.txt "# Ingcool 7in touch screen" "max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 1024 600 60 6 0 0 0
hdmi_drive=1"

        print_warning "usb_max_current_enable=1 raises the Pi 5 USB power limit; use a suitable power supply."
        if ask_yes_no "Do you want to enable the higher USB current limit for the touchscreen?"; then
            # Keep this outside the block so existing installations receive it too.
            append_root_line_if_missing /boot/firmware/config.txt "usb_max_current_enable=1"
        fi
        
        print_success "Ingcool touchscreen configured"
        NEED_REBOOT=true
    else
        print_info "Skipping Ingcool touchscreen configuration"
    fi
else
    print_info "Step 4/9: Ingcool Touchscreen (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 5: Raspberry Pi Camera Module V3 (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 5/9: Do you want to configure Raspberry Pi Camera Module V3?"; then
        print_info "Configuring Pi Camera Module V3..."

        if [ "$SKIP_ONLINE_STEPS" = true ]; then
            print_warning "Skipping Picamera2 installation because Internet is unavailable"
        else
            sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y python3-picamera2 rpicam-apps
            "$PHOTOBOOTH_PYTHON" -c 'from picamera2 import Picamera2; from libcamera import controls, Transform; print("Camera binding imports OK; test the sensor after reboot")'
        fi
        
        # Allocate more memory
        replace_or_append_root_line /boot/firmware/config.txt '^dtoverlay=vc4-kms-v3d$' 'dtoverlay=vc4-kms-v3d,cma-512'
        
        # Enable camera
        append_root_block_if_missing /boot/firmware/config.txt "# Camera module 3" "dtoverlay=imx708,cam0"
        
        print_success "Pi Camera Module V3 configured"
        print_warning "After reboot, you can test the camera with: rpicam-hello --list-cameras"
        NEED_REBOOT=true
    else
        print_info "Skipping Pi Camera configuration"
    fi
else
    print_info "Step 5/9: Pi Camera Module (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 6: DSLR Support with gPhoto2
# ============================================================================
echo ""
if ask_yes_no "Step 6/9: Do you want to install DSLR support (gPhoto2)?"; then
    if [ "$SKIP_ONLINE_STEPS" = true ]; then
        print_warning "Skipping gPhoto2 installation because Internet is unavailable"
    else
        print_info "Installing gPhoto2..."
        
        # Use the distribution's signed packages instead of a remote root script.
        sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y gphoto2
        
        print_success "gPhoto2 installed"
        print_warning "Eject/unmount the camera in your file manager and reconnect it before testing: gphoto2 --capture-image-and-download"
    fi

    # This local workaround also applies to an already-installed, offline setup.
    print_warning "The GVFS USB workaround disables desktop camera browsing/import for all users. Package updates may undo it."
    if ask_yes_no "Do you want to disable GVFS camera access to avoid gPhoto2 USB claim errors (-53)?"; then
        for gvfs_dir in /usr/lib/gvfs /usr/libexec; do
            for gvfs_binary in gvfs-gphoto2-volume-monitor gvfsd-gphoto2; do
                if [ -f "$gvfs_dir/$gvfs_binary" ]; then
                    sudo chmod a-x "$gvfs_dir/$gvfs_binary"
                fi
            done
        done
        if command_exists killall; then
            # Only stop this user's camera processes; no running process is normal.
            killall gvfs-gphoto2-volume-monitor gvfsd-gphoto2 2>/dev/null || true
        else
            print_warning "killall is unavailable; log out and back in to stop existing GVFS camera processes."
        fi
        print_info "Eject/unmount the camera in your file manager and reconnect it before testing."
    fi
    print_info "With the photobooth stopped, test manually: gphoto2 --auto-detect"
    print_info "Then test capture: gphoto2 --capture-image-and-download"
else
    print_info "Skipping gPhoto2 installation"
fi
echo ""

# ============================================================================
# STEP 7: CUPS Printer Support
# ============================================================================
echo ""
if ask_yes_no "Step 7/9: Do you want to install printer support (CUPS)?"; then
    if [ "$SKIP_ONLINE_STEPS" = true ]; then
        print_warning "Skipping CUPS installation because Internet is unavailable"
    else
        print_info "Installing CUPS..."
        
        sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y cups libcups2-dev python3-cups printer-driver-gutenprint
        sudo usermod -a -G lpadmin "$USER"
        print_warning "Remote CUPS administration exposes the printer server to network clients, including the open PhotoBooth AP."
        if ask_yes_no "Do you want to allow remote CUPS administration from any network?"; then
            sudo cupsctl --remote-admin --remote-any
        else
            sudo cupsctl --no-remote-admin --no-remote-any
        fi
        "$PHOTOBOOTH_PYTHON" -c 'import cups; print("CUPS binding import OK")'
        
        # Install printer drivers
        sudo install -m 644 "$SCRIPT_DIR/docs/DS620.ppd" /usr/share/cups/model/DS620.ppd
        
        # Restart CUPS
        sudo /etc/init.d/cups restart
        
        print_success "CUPS and DS620 PPD installed"
        print_info "Configure your printer locally at: http://localhost:631/admin/ (or use SSH port forwarding)"
        print_warning "Remember to name your printer 'DS620' (or update config.ini accordingly)"
    fi
else
    print_info "Skipping CUPS installation"
fi
echo ""

# ============================================================================
# STEP 8: LED Ring Support (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 8/9: Do you want to install WS2812 LED Ring support?"; then
        print_info "Configuring LED Ring support..."
        
        # Enable SPI
        if sudo grep -Fqx 'dtparam=spi=on' /boot/firmware/config.txt; then
            :
        elif sudo grep -Fqx '#dtparam=spi=on' /boot/firmware/config.txt; then
            sudo sed -i 's/^#dtparam=spi=on$/dtparam=spi=on/' /boot/firmware/config.txt
        else
            append_root_line_if_missing /boot/firmware/config.txt 'dtparam=spi=on'
        fi
        
        # Install Python dependency
        if [ "$SKIP_ONLINE_STEPS" = true ]; then
            print_warning "Skipping spidev installation because Internet is unavailable"
        else
            "$PHOTOBOOTH_PYTHON" -m pip install spidev
        fi
        
        print_success "LED Ring support configured"
        print_info "Connect LED Ring: GND to Pin 6/9/14/20/25, DIN to Pin 19 (GPIO 10), VCC to Pin 2/4 (5V)"
        NEED_REBOOT=true
    else
        print_info "Skipping LED Ring configuration"
    fi
else
    print_info "Step 8/9: LED Ring Support (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 9: WiFi Access Point Setup (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    print_warning "AP setup replaces /etc/dnsmasq.conf (backup saved), takes over wlan0 and can disconnect SSH. Use Ethernet or a local console."
    if ask_yes_no "Step 9/9: Do you want to configure WiFi Access Point for photo downloads?"; then
        if [ "$SKIP_ONLINE_STEPS" = true ]; then
            print_warning "Skipping WiFi Access Point setup because Internet is unavailable"
        else
            USE_NETWORK_MANAGER=false
            if systemctl is-active --quiet NetworkManager.service; then
                USE_NETWORK_MANAGER=true
            elif ! systemctl is-active --quiet dhcpcd.service; then
                print_error "Neither NetworkManager nor dhcpcd is active; AP setup cannot proceed safely."
                exit 1
            fi
            WIFI_COUNTRY=$(get_wifi_country) || {
                print_error "Unable to detect the WiFi country. Configure it with raspi-config, then run this installer again."
                exit 1
            }
            print_info "Configuring WiFi Access Point..."
            
            # Install required packages
            print_info "Installing hostapd and dnsmasq..."
            sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y hostapd dnsmasq iptables
            
            # Stop services during configuration
            print_info "Stopping services..."
            sudo systemctl stop hostapd 2>/dev/null || true
            sudo systemctl stop dnsmasq 2>/dev/null || true
            
            # Backup original configuration files
            print_info "Backing up original configurations..."
            backup_root_file_once /etc/dhcpcd.conf
            backup_root_file_once /etc/dnsmasq.conf
            backup_root_file_once /etc/hostapd/hostapd.conf
            backup_root_file_once /etc/NetworkManager/conf.d/unmanaged-wlan0.conf
            backup_root_file_once /etc/systemd/system/photobooth-ap-network.service
            backup_root_file_once /etc/systemd/system/photobooth-http-redirect.service
            
            # Configure static IP for wlan0 using the active network manager
            if [ "$USE_NETWORK_MANAGER" = true ]; then
                print_info "Configuring NetworkManager to ignore wlan0..."
                write_root_file_if_changed "/etc/NetworkManager/conf.d/unmanaged-wlan0.conf" "$(cat <<'EOF'
[keyfile]
unmanaged-devices=interface-name:wlan0
EOF
)"

                print_info "Creating static IP service for wlan0..."
                write_root_file_if_changed "/etc/systemd/system/photobooth-ap-network.service" "$(cat <<'EOF'
[Unit]
Description=Static IP for PhotoBooth AP
Before=hostapd.service dnsmasq.service photobooth-http-redirect.service
Wants=hostapd.service dnsmasq.service photobooth-http-redirect.service

[Service]
Type=oneshot
ExecStartPre=/usr/sbin/rfkill unblock wifi
ExecStartPre=/bin/sh -c "systemctl stop wpa_supplicant@wlan0.service 2>/dev/null || true"
ExecStart=/sbin/ip link set wlan0 up
ExecStart=/sbin/ip addr flush dev wlan0
ExecStart=/sbin/ip addr add 192.168.4.1/24 dev wlan0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
)"
            else
                print_info "Configuring static IP for wlan0 via dhcpcd..."
                append_root_block_if_missing /etc/dhcpcd.conf "# PhotoBooth WiFi AP Configuration" "interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant"
            fi
            
            # Configure dnsmasq (DHCP and DNS server)
            print_info "Configuring dnsmasq..."
            write_root_file_if_changed "/etc/dnsmasq.conf" "$(cat <<'EOF'
# PhotoBooth WiFi AP Configuration
interface=wlan0
bind-interfaces
dhcp-authoritative
dhcp-range=192.168.4.10,192.168.4.100,255.255.255.0,24h
domain=photobooth.local

# Tell phones to use the PhotoBooth as gateway and DNS server.
# Without this, some phones keep routing through 4G/5G instead of opening the local portal.
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1

# Captive Portal DNS - resolve every domain to the PhotoBooth.
# Phones probe public domains to detect captive portals; this makes those probes hit Flask locally.
address=/#/192.168.4.1

# Explicit captive portal probe domains kept for readability/debugging.
address=/captive.apple.com/192.168.4.1
address=/www.apple.com/192.168.4.1
address=/apple.com/192.168.4.1
address=/connectivitycheck.gstatic.com/192.168.4.1
address=/clients3.google.com/192.168.4.1
address=/msftconnecttest.com/192.168.4.1
address=/www.msftconnecttest.com/192.168.4.1
address=/msftncsi.com/192.168.4.1
address=/www.msftncsi.com/192.168.4.1
address=/detectportal.firefox.com/192.168.4.1
address=/nmcheck.gnome.org/192.168.4.1

# Logging (optional, comment out for production)
log-queries
log-dhcp
EOF
)"

            # Redirect HTTP traffic from port 80 to the application on port 5000
            print_info "Creating HTTP redirect service (80 -> 5000)..."
            write_root_file_if_changed "/etc/systemd/system/photobooth-http-redirect.service" "$(cat <<'EOF'
[Unit]
Description=Redirect HTTP traffic to PhotoBooth web app
After=photobooth-ap-network.service hostapd.service
Wants=photobooth-ap-network.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c "/usr/sbin/iptables -t nat -C PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-ports 5000 2>/dev/null || /usr/sbin/iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-ports 5000"
ExecStop=/bin/sh -c "/usr/sbin/iptables -t nat -D PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-ports 5000 2>/dev/null || true"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
)"
            
            # Configure hostapd (WiFi Access Point)
            print_info "Configuring hostapd..."
            print_info "Using WiFi country: $WIFI_COUNTRY"
            write_root_file_if_changed "/etc/hostapd/hostapd.conf" "$(cat <<EOF
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

# Country code detected from Raspberry Pi OS, the regulatory domain, or locale
country_code=$WIFI_COUNTRY

# Beacon interval
beacon_int=100

# DTIM period
dtim_period=2
EOF
)"
            
            # Tell hostapd where to find the config file
            print_info "Updating hostapd daemon configuration..."
            write_root_file_if_changed "/etc/default/hostapd" "$(cat <<'EOF'
# Defaults for hostapd initscript
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF
)"

            if [ "$USE_NETWORK_MANAGER" = true ]; then
                print_info "Making hostapd wait for wlan0 AP setup..."
                write_root_file_if_changed "/etc/systemd/system/hostapd.service.d/photobooth-ap.conf" "$(cat <<'EOF'
[Unit]
After=photobooth-ap-network.service
Requires=photobooth-ap-network.service

[Service]
ExecStartPre=/usr/sbin/rfkill unblock wifi
EOF
)"
            fi
            
            # Unmask and enable services
            print_info "Enabling services..."
            sudo systemctl unmask hostapd
            sudo systemctl enable hostapd
            sudo systemctl enable dnsmasq
            sudo systemctl daemon-reload
            sudo systemctl enable photobooth-http-redirect.service
            if [ "$USE_NETWORK_MANAGER" = true ]; then
                sudo systemctl enable photobooth-ap-network.service
            fi
            
            # Start services
            print_info "Starting services..."
            if [ "$USE_NETWORK_MANAGER" = true ]; then
                sudo nmcli general reload conf
                sudo nmcli device set wlan0 managed no
                sudo systemctl restart photobooth-ap-network.service
            else
                sudo systemctl restart dhcpcd
            fi
            sudo systemctl restart hostapd || { sudo journalctl -xeu hostapd.service --no-pager; exit 1; }
            sudo systemctl restart dnsmasq
            sudo systemctl restart photobooth-http-redirect.service
            
            print_success "WiFi Access Point configured"
            print_info "SSID: PhotoBooth"
            print_info "IP Address: 192.168.4.1"
            print_info "Web Server: http://192.168.4.1 (redirected to port 5000)"
            print_info "Captive Portal: DNS wildcard and HTTP redirect configured"
            NEED_REBOOT=true
        fi
    else
        print_info "Skipping WiFi Access Point configuration"
    fi
else
    print_info "Step 9/9: WiFi Access Point (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# OPTIONAL: Autostart on Boot
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Do you want the photobooth to start automatically on boot?"; then
        print_info "Configuring systemd photobooth service..."

        PHOTOBOOTH_DIR="$SCRIPT_DIR"
        PHOTOBOOTH_USER=$(id -un)
        PHOTOBOOTH_GROUP=$(id -gn)
        PHOTOBOOTH_DIR_ESCAPED=$(escape_systemd_value "$PHOTOBOOTH_DIR")
        PHOTOBOOTH_PYTHON_ESCAPED=$(escape_systemd_value "$PHOTOBOOTH_PYTHON")
        PHOTOBOOTH_APP_ESCAPED=$(escape_systemd_value "$PHOTOBOOTH_DIR/photoboothapp.py")

        write_root_file_if_changed "/etc/systemd/system/photobooth.service" "$(cat <<EOF
[Unit]
Description=Simple PhotoBooth application
After=display-manager.service
# The UI may exit repeatedly while the graphical session is coming up.  Do not
# permanently stop recovery after the systemd start-rate limit is reached.
StartLimitIntervalSec=0

[Service]
Type=simple
User=$PHOTOBOOTH_USER
Group=$PHOTOBOOTH_GROUP
WorkingDirectory=$PHOTOBOOTH_DIR_ESCAPED
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:0
Environment=XDG_SESSION_TYPE=wayland
ExecStartPre=/bin/bash -lc 'uid=\$\$(id -u); runtime="/run/user/\$\$uid"; attempt=0; while [ "\$\$attempt" -lt 30 ]; do for socket in "\$\$runtime"/wayland-*; do if [ -S "\$\$socket" ]; then exit 0; fi; done; sleep 1; attempt=\$\$((attempt + 1)); done; echo "No Wayland socket found in \$\$runtime" >&2; exit 1'
ExecStart=/bin/bash -lc 'uid=\$\$(id -u); export XDG_RUNTIME_DIR="/run/user/\$\$uid"; export DISPLAY="\$\${DISPLAY:-:0}"; export XDG_SESSION_TYPE="\$\${XDG_SESSION_TYPE:-wayland}"; for socket in "\$\$XDG_RUNTIME_DIR"/wayland-*; do if [ -S "\$\$socket" ]; then export WAYLAND_DISPLAY="\$\${socket##*/}"; break; fi; done; exec $PHOTOBOOTH_PYTHON_ESCAPED $PHOTOBOOTH_APP_ESCAPED'
Restart=always
RestartSec=5
KillMode=control-group
TimeoutStopSec=15
StandardOutput=append:/var/log/photobooth.log
StandardError=append:/var/log/photobooth.log

[Install]
WantedBy=graphical.target
EOF
)"

        sudo touch /var/log/photobooth.log
        sudo chown "$PHOTOBOOTH_USER:$PHOTOBOOTH_GROUP" /var/log/photobooth.log
        sudo systemctl daemon-reload
        sudo systemctl unmask photobooth.service >/dev/null 2>&1 || true
        sudo systemctl enable photobooth.service

        print_success "systemd service configured"
        print_info "Photobooth will start automatically on boot and wait for the Wayland session before launching"
    else
        print_info "Skipping autostart configuration"
    fi
fi
echo ""

# ============================================================================
# Installation Complete
# ============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║            Installation Complete!                     ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

print_success "Selected installation steps completed"
echo ""

# Summary
print_info "Installation Summary:"
if [ "$SKIP_ONLINE_STEPS" = true ]; then
    print_warning "Package installations skipped (offline); existing dependencies were not verified."
else
    print_success "Base dependencies installed; application dependency imports checked."
fi
print_info "Camera capture, display, printing and network operation still require hardware testing."

if [ "$NEED_REBOOT" = true ]; then
    echo ""
    print_warning "A system reboot is required to apply all changes"
    echo ""
    if ask_yes_no "Do you want to reboot now?"; then
        print_info "Rebooting system..."
        sudo reboot
    else
        print_warning "Please reboot your system manually to apply all changes"
        print_info "Run: sudo reboot"
    fi
fi

echo ""
print_info "To start the photobooth manually, run:"
echo "  cd $SCRIPT_DIR"
echo "  \"$PHOTOBOOTH_PYTHON\" photoboothapp.py"
echo ""
print_info "For more information, see INSTALLATION.md and README.md"
echo ""

exit 0
