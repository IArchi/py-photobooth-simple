# Installation Guide

This guide will help you install and configure the Simple PhotoBooth application on your Raspberry Pi or other compatible systems.

## System Requirements

- Raspberry Pi 5 (8GB recommended) or compatible system
- Raspberry Pi OS (Debian-based)
- Python 3.x
- Internet connection for initial setup

## Quick Installation

For automated installation, you can use the installation script:

```bash
chmod +x install.sh
./install.sh
```

The script will guide you through the installation process and ask which components you want to install.

## Manual Installation

### 1. Global Packages

Install system dependencies and Python packages:

```bash
# Update system
sudo apt update

# Install build dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev

# Install Python dependencies
pip3 install -r requirements.txt --break-system-packages
```

### 2. Kiosk Mode Configuration (Optional)

To run the photobooth in kiosk mode on Raspberry Pi:

```bash
# Hide mouse cursor and background panel
sudo sed -i 's/\[autostart\]/\[autostart]\r\background = wf-background/g /etc/wayfire/defaults.ini

# Hide taskbar
sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini

# Disable power warning
echo "avoid_warnings=1" | sudo tee -a /boot/firmware/config.txt && sudo apt remove lxplug-ptbatt -y

# Disable media mount dialog
sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/LXDE-pi/pcmanfm.conf
sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/default/pcmanfm.conf

# Reboot to apply changes
sudo reboot
```

### 3. Ingcool 7" Touchscreen Configuration (Optional)

If you're using the Ingcool 7" touchscreen:

```bash
sudo sh -c "echo '# Ingcool 7in touch screen' >> /boot/firmware/config.txt"
sudo sh -c "echo 'max_usb_current=1' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_group=2' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_mode=87' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_cvt 1024 600 60 6 0 0 0' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_drive=1' >> /boot/firmware/config.txt"
sudo sh -c "echo '' >> /boot/firmware/config.txt"

# Reboot to apply changes
sudo reboot
```

### 4. Raspberry Pi Camera Module V3 Setup (Recommended)

If you're using the Raspberry Pi Camera Module V3:

```bash
# Allocate more memory for camera
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt

# Enable camera overlay
sudo sh -c "echo '# Camera module 3' >> /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=imx708,cam0' >> /boot/firmware/config.txt"
sudo sh -c "echo '' >> /boot/firmware/config.txt"

# Reboot to apply changes
sudo reboot

# Test camera after reboot
libcamera-still --list-camera
libcamera-still --autofocus-mode=auto -f -o test.jpg
```

### 5. DSLR Camera Support with GPhoto2 (Optional)

If you plan to use a DSLR camera:

```bash
# Download and install gPhoto2 updater
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/.env
chmod +x gphoto2-updater.sh
sudo ./gphoto2-updater.sh -s
rm gphoto2-updater.sh .env

# Fix USB access issues
sudo chmod -x /usr/lib/gvfs/gvfs-gphoto2-volume-monitor
sudo chmod -x /usr/lib/gvfs/gvfsd-gphoto2

# Test camera connection
gphoto2 --capture-image
```

### 6. Printer Setup with CUPS (Optional)

If you want to print photos directly from the photobooth:

```bash
# Install CUPS and drivers
sudo apt-get install -y cups libcups2-dev python3-cups
sudo usermod -a -G lpadmin $USER
sudo cupsctl --remote-admin --remote-any

# Install driverless printer support
sudo apt install -y printer-driver-gutenprint

# Restart CUPS service
sudo /etc/init.d/cups restart
```

**Printer Configuration:**
1. Connect your printer via USB
2. Open a web browser and navigate to `https://<raspberry-ip>:631/admin/`
3. Click "Add Printer" (you'll need to enter your SSH credentials)
4. Select your printer from the list
5. Name it `DS620` (or update the name in `config.ini` to match)
6. Select the appropriate brand and model (e.g., DNP DS620)

### 7. LED Ring Configuration (Optional)

If you're using a WS2812 LED ring:

```bash
# Enable SPI interface
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt

# Install Python SPI library
pip3 install spidev --break-system-packages

# Reboot to apply changes
sudo reboot
```

**LED Ring Wiring:**

Connect your WS2812 LED ring to the Raspberry Pi GPIO pins:

| WS2812 Pin | Raspberry Pi Pin           |
|------------|----------------------------|
| GND        | Pin 6, 9, 14, 20, or 25    |
| DIN        | Pin 19 (MOSI, GPIO 10)     |
| VCC        | Pin 2 or 4 (5V)            |

### 8. Autostart on Boot (Optional)

To automatically start the photobooth when the Raspberry Pi boots:

```bash
# Create autostart configuration
echo '[autostart]' >> ~/.config/wayfire.ini
echo 'photobooth = /home/pi/photobooth.sh' >> ~/.config/wayfire.ini

# Create startup script
echo '#!/bin/bash' > /home/pi/photobooth.sh
echo 'cd /home/pi/photobooth/' >> /home/pi/photobooth.sh
echo 'python3 photoboothapp.py' >> /home/pi/photobooth.sh
chmod +x /home/pi/photobooth.sh
```

**Note:** Adjust the path in the script if you've installed the photobooth in a different location.

## Running the Application

To start the photobooth manually:

```bash
cd /path/to/photobooth
python3 photoboothapp.py
```

## Configuration

You can customize the photobooth behavior by editing `config.ini`:

- **Autorestart on failure:** Automatically restart if the app crashes
- **Full screen mode:** Run in fullscreen or windowed mode
- **Countdown duration:** Time before capturing the photo
- **Storage directories:** Where photos and collages are saved
- **Printer name:** CUPS printer name for printing
- **Calibration matrix:** For hybrid camera setups (DSLR + piCamera)
- **Overlays:** Custom overlay images for photos

## Troubleshooting

### Camera Not Detected

- **Pi Camera:** Check cable connection and ensure camera is enabled in `raspi-config`
- **DSLR:** Ensure gPhoto2 is properly installed and camera is compatible
- **Webcam:** Check USB connection and camera permissions

### Printer Not Working

- Verify printer is connected via USB
- Check CUPS web interface (`https://<raspberry-ip>:631/`)
- Ensure printer is set as default and named correctly in `config.ini`
- Check printer driver installation

### LED Ring Not Lighting

- Verify SPI is enabled in `/boot/firmware/config.txt`
- Check wiring connections
- Ensure LED ring is powered with 5V
- Test with a simple SPI test script

### Screen Resolution Issues

- For Ingcool screen, verify HDMI configuration in `/boot/firmware/config.txt`
- For other screens, adjust `hdmi_mode` and `hdmi_cvt` settings accordingly
- Check screen documentation for recommended settings

## USB Photo Dump

The photobooth automatically detects USB drives and copies all photos:

- Insert a FAT32-formatted USB drive
- The application will automatically copy photos to the drive
- Wait for the copy process to complete (screen will show progress)
- Safely remove the USB drive when prompted

**Important:** USB drives must be formatted as FAT32 for compatibility.

## Support and Updates

For updates, bug reports, or feature requests, please visit the project repository.
