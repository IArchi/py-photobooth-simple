# Installation Guide

This guide will help you install and configure the Simple PhotoBooth application on your Raspberry Pi or other compatible systems.

## System Requirements

- Raspberry Pi 5 (8GB recommended) or compatible system
- Raspberry Pi OS (Debian-based)
- Python 3.x
- Internet connection for initial setup

Use the distribution's Python for access to native camera bindings. Raspberry Pi OS
and generic Debian are not interchangeable for camera support: generic Debian needs
a working Raspberry Pi libcamera stack. Trixie / Python 3.13 is not yet hardware-validated
by this project; successful installation alone does not validate camera operation.

## Quick Installation

For automated installation, you can use the installation script:

```bash
chmod +x install.sh
./install.sh
```

The script will guide you through the installation process and ask which components you want to install.
It creates or reuses `.venv` with access to system Python packages, without bypassing
PEP 668. Both the generated systemd service and manual launch use that environment.

## Manual Installation

### 1. System Packages and Virtual Environment

Install system dependencies and Python packages:

```bash
# Update system
sudo apt update

# Install build dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip python3-venv libgl1 libgphoto2-dev

# Install Python dependencies
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run these commands from the project directory. `pip --user` is also blocked by
PEP 668; do not use `sudo pip` or `--break-system-packages`. The system-packages
option exposes APT-installed Picamera2, libcamera and CUPS bindings to the venv.
Use the same distribution Python version as those bindings, not a separate pyenv
or manually compiled Python. Re-running the venv command enables system packages
in an existing venv; if it was created with another Python version, move it aside
and create a fresh one before reinstalling requirements.

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
sudo sh -c "echo 'usb_max_current_enable=1' >> /boot/firmware/config.txt"
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
# Install the matching Picamera2/libcamera stack from Raspberry Pi OS repositories
sudo apt install -y python3-picamera2 rpicam-apps

# Allocate more memory for camera
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt

# Enable camera overlay
sudo sh -c "echo '# Camera module 3' >> /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=imx708,cam0' >> /boot/firmware/config.txt"
sudo sh -c "echo '' >> /boot/firmware/config.txt"

# Reboot to apply changes
sudo reboot

# Test camera after reboot
rpicam-hello --list-cameras
rpicam-still --autofocus-mode=auto -o test.jpg
```

After reboot, from the project directory, check the actual application interpreter:

```bash
.venv/bin/python -c 'from picamera2 import Picamera2; from libcamera import controls, Transform; print(Picamera2.global_camera_info())'
```

Prefer APT over `pip install picamera2`: Picamera2 and libcamera must be compatible.
On older images, camera utilities may be named `libcamera-hello` / `libcamera-still`.
The installer configures the IMX708 Module 3 on CAM0; do not apply that overlay to
another sensor or connector. The application's Pi backend currently configures
autofocus, so fixed-focus modules are not validated by this setup.

### 5. DSLR Camera Support with GPhoto2 (Optional)

If you plan to use a DSLR camera:

```bash
# Download and install gPhoto2 updater
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/.env
chmod +x gphoto2-updater.sh
sudo ./gphoto2-updater.sh -s
rm gphoto2-updater.sh .env

# Test with the photobooth stopped and the camera unmounted in the file manager
gphoto2 --auto-detect
gphoto2 --capture-image-and-download
```

The Canon EOS 600D is supported for capture and preview by upstream libgphoto2;
this does not imply model-specific hardware validation by this project. Set JPEG
capture on the camera because the application decodes the downloaded image with OpenCV.

#### Hybrid preview and capture

When both cameras initialize successfully, the application automatically uses
Picamera2 for live preview and gPhoto2 for the final photo after the countdown.
Look for `Switch to hybrid camera (Picamera + gPhoto2)` in the logs. The Canon's
liveview is not required during normal hybrid operation. If either backend fails,
the application falls back to another available camera configuration.

For framing alignment, use `[Capture] CALIBRATION` in `config.ini` and the existing
`tools/calibrate_zoom.py` utility. Unlike normal hybrid operation, this utility
requires a working DSLR preview. Calibration does not remove depth-dependent parallax.

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
.venv/bin/python -m pip install spidev

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
echo 'exec /home/pi/photobooth/.venv/bin/python photoboothapp.py' >> /home/pi/photobooth.sh
chmod +x /home/pi/photobooth.sh
```

**Note:** Adjust the path in the script if you've installed the photobooth in a different location.
This is an alternative to the installer's systemd service; do not enable both.
For an existing service, rerun the installer's autostart setup or update its Python
path to the project's `.venv/bin/python`, then reload systemd and restart the service.

## Running the Application

To start the photobooth manually:

```bash
cd /path/to/photobooth
.venv/bin/python photoboothapp.py
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

### Picamera2 Unavailable in a Virtual Environment

Run the import check in the camera setup section. The application warning can mean
an import failed, no sensor was found, or initialization failed; inspect preceding
`Picamera2Camera` errors too. If the system Python imports Picamera2 but the venv
does not, check `include-system-site-packages = true` in `.venv/pyvenv.cfg` and
recreate the environment with the distribution Python if necessary. If the logs
report a NumPy ABI mismatch, check the installed NumPy and native extension versions:
a pip-installed NumPy can shadow the version required by APT camera packages.

### gPhoto2: Could Not Claim the USB Device (-53)

This means libgphoto2 could not claim the USB interface, not that the model is
unsupported. Another process holding the camera is a common cause.

1. Stop the application and, if enabled, `sudo systemctl stop photobooth.service`.
2. Close photo importers and other camera software. Unmount/eject the camera's
   filesystem connection in the desktop file manager without disconnecting USB.
   `gio mount -l` lists desktop mounts; `gio mount -u 'gphoto2://…'` can unmount
   the exact camera URI shown there. GVFS may remount it, so disable camera
   auto-import in desktop settings if needed. Do not change executable permissions
   on system GVFS binaries.
3. Run `gphoto2 --auto-detect`, then `gphoto2 --capture-image-and-download` as the
   same user as the application. Detection alone does not prove capture works.
4. If claiming still fails, inspect the device's udev permissions and the installed
   libgphoto2 rules, then try another data cable/USB port and check Pi power stability.

Do not test the CLI while the application owns the Canon, or run the whole
photobooth as root to work around permissions.

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
