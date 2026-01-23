#!/bin/bash

# Simple PhotoBooth - Automated Installation Script
# This script will guide you through the installation process

set -e  # Exit on error

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

# Ask yes/no question
ask_yes_no() {
    while true; do
        read -p "$1 (y/n): " yn
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

# Banner
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

# ============================================================================
# STEP 1: Base System Dependencies
# ============================================================================
print_info "Step 1/8: Installing base system dependencies..."

sudo apt update
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev

print_success "Base dependencies installed"
echo ""

# ============================================================================
# STEP 2: Python Dependencies
# ============================================================================
print_info "Step 2/8: Installing Python dependencies..."

pip3 install -r requirements.txt --break-system-packages

print_success "Python dependencies installed"
echo ""

# ============================================================================
# STEP 3: Kiosk Mode (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 3/8: Do you want to enable Kiosk Mode (hide mouse, taskbar, etc.)?"; then
        print_info "Configuring Kiosk Mode..."
        
        # Hide mouse and panel
        sudo sed -i 's/\[autostart\]/\[autostart\]\r\background = wf-background/g' /etc/wayfire/defaults.ini
        
        # Hide taskbar
        sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini
        
        # Disable power warning
        echo "avoid_warnings=1" | sudo tee -a /boot/firmware/config.txt > /dev/null
        sudo apt remove lxplug-ptbatt -y || true
        
        # Disable media mount dialog
        sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/LXDE-pi/pcmanfm.conf || true
        sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/default/pcmanfm.conf || true
        
        print_success "Kiosk Mode configured"
        NEED_REBOOT=true
    else
        print_info "Skipping Kiosk Mode configuration"
    fi
else
    print_info "Step 3/8: Kiosk Mode (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 4: Ingcool 7" Touchscreen (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 4/8: Are you using the Ingcool 7\" touchscreen?"; then
        print_info "Configuring Ingcool 7\" touchscreen..."
        
        sudo sh -c "echo '# Ingcool 7in touch screen' >> /boot/firmware/config.txt"
        sudo sh -c "echo 'max_usb_current=1' >> /boot/firmware/config.txt"
        sudo sh -c "echo 'hdmi_group=2' >> /boot/firmware/config.txt"
        sudo sh -c "echo 'hdmi_mode=87' >> /boot/firmware/config.txt"
        sudo sh -c "echo 'hdmi_cvt 1024 600 60 6 0 0 0' >> /boot/firmware/config.txt"
        sudo sh -c "echo 'hdmi_drive=1' >> /boot/firmware/config.txt"
        sudo sh -c "echo '' >> /boot/firmware/config.txt"
        
        print_success "Ingcool touchscreen configured"
        NEED_REBOOT=true
    else
        print_info "Skipping Ingcool touchscreen configuration"
    fi
else
    print_info "Step 4/8: Ingcool Touchscreen (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 5: Raspberry Pi Camera Module V3 (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 5/8: Do you want to configure Raspberry Pi Camera Module V3?"; then
        print_info "Configuring Pi Camera Module V3..."
        
        # Allocate more memory
        sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt
        
        # Enable camera
        sudo sh -c "echo '# Camera module 3' >> /boot/firmware/config.txt"
        sudo sh -c "echo 'dtoverlay=imx708,cam0' >> /boot/firmware/config.txt"
        sudo sh -c "echo '' >> /boot/firmware/config.txt"
        
        print_success "Pi Camera Module V3 configured"
        print_warning "After reboot, you can test the camera with: libcamera-still --list-camera"
        NEED_REBOOT=true
    else
        print_info "Skipping Pi Camera configuration"
    fi
else
    print_info "Step 5/8: Pi Camera Module (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# STEP 6: DSLR Support with gPhoto2
# ============================================================================
echo ""
if ask_yes_no "Step 6/8: Do you want to install DSLR support (gPhoto2)?"; then
    print_info "Installing gPhoto2..."
    
    # Download and run gPhoto2 updater
    cd /tmp
    wget -q https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh
    wget -q https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/.env
    chmod +x gphoto2-updater.sh
    
    print_info "Running gPhoto2 updater (this may take several minutes)..."
    sudo ./gphoto2-updater.sh -s
    
    rm -f gphoto2-updater.sh .env
    cd - > /dev/null
    
    # Fix USB access issues
    sudo chmod -x /usr/lib/gvfs/gvfs-gphoto2-volume-monitor || true
    sudo chmod -x /usr/lib/gvfs/gvfsd-gphoto2 || true
    
    print_success "gPhoto2 installed"
    print_warning "After installation, test with: gphoto2 --capture-image"
else
    print_info "Skipping gPhoto2 installation"
fi
echo ""

# ============================================================================
# STEP 7: CUPS Printer Support
# ============================================================================
echo ""
if ask_yes_no "Step 7/8: Do you want to install printer support (CUPS)?"; then
    print_info "Installing CUPS..."
    
    sudo apt-get install -y cups libcups2-dev python3-cups
    sudo usermod -a -G lpadmin $USER
    sudo cupsctl --remote-admin --remote-any
    
    # Install printer drivers
    sudo apt install -y printer-driver-gutenprint
    
    # Restart CUPS
    sudo /etc/init.d/cups restart
    
    print_success "CUPS installed"
    print_info "Configure your printer at: https://$(hostname -I | awk '{print $1}'):631/admin/"
    print_warning "Remember to name your printer 'DS620' (or update config.ini accordingly)"
else
    print_info "Skipping CUPS installation"
fi
echo ""

# ============================================================================
# STEP 8: LED Ring Support (Raspberry Pi only)
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Step 8/8: Do you want to install WS2812 LED Ring support?"; then
        print_info "Configuring LED Ring support..."
        
        # Enable SPI
        sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
        
        # Install Python dependency
        pip3 install spidev --break-system-packages
        
        print_success "LED Ring support configured"
        print_info "Connect LED Ring: GND to Pin 6/9/14/20/25, DIN to Pin 19 (GPIO 10), VCC to Pin 2/4 (5V)"
        NEED_REBOOT=true
    else
        print_info "Skipping LED Ring configuration"
    fi
else
    print_info "Step 8/8: LED Ring Support (Raspberry Pi only) - Skipped (not on Raspberry Pi)"
fi
echo ""

# ============================================================================
# OPTIONAL: Autostart on Boot
# ============================================================================
if is_raspberry_pi; then
    echo ""
    if ask_yes_no "Do you want the photobooth to start automatically on boot?"; then
        print_info "Configuring autostart..."
        
        PHOTOBOOTH_DIR=$(pwd)
        
        # Create autostart configuration
        mkdir -p ~/.config
        if ! grep -q "photobooth" ~/.config/wayfire.ini 2>/dev/null; then
            echo '[autostart]' >> ~/.config/wayfire.ini
            echo "photobooth = $HOME/photobooth.sh" >> ~/.config/wayfire.ini
        fi
        
        # Create startup script
        cat > $HOME/photobooth.sh << EOF
#!/bin/bash
cd $PHOTOBOOTH_DIR
python3 photoboothapp.py
EOF
        chmod +x $HOME/photobooth.sh
        
        print_success "Autostart configured"
        print_info "Photobooth will start automatically on boot"
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

print_success "Simple PhotoBooth has been installed successfully!"
echo ""

# Summary
print_info "Installation Summary:"
echo "  ✓ Base dependencies installed"
echo "  ✓ Python packages installed"

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
echo "  cd $(pwd)"
echo "  python3 photoboothapp.py"
echo ""
print_info "For more information, see INSTALLATION.md and README.md"
echo ""

exit 0
