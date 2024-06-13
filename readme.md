# Simple PhotoBooth

I wanted to create a very simple to use photobooth without unecessary features.
This project is easy to edit and has been tested on 3 to 5 years old child to ensure it was easy to understand the way to use it.

## State machine
It relies on a state machine to display screens.
![State Machine](doc/state_machine.png)

## Screens
![Waiting screen](doc/waiting.png)
![Select format](doc/select_format.png)
![Print screen](doc/print.png)

## Cameras
The application is compatible with piCamera, DSLR and CV2 devices.
By default, it will try to use the best available quality:
 - If piCamera is connected, it will be used for preview ;
 - If DSLR is connected, it will be used for capture ;

If one of these is not available, it will use the first available one.

## Wiring of WS2812 Ring Led
Connect WS2812 Ring led on the following GPIO pins:
 - GND   --   GND. At least one of pin 6, 9, 14, 20, 25
 - DIN   --   MOSI, Pin 19, GPIO 10
 - VCC   --   5V. At least one of pin 2 or 4

## Compatibility
Tested on MacOs Sonoma and RaspberryPi 5 8GB with Arducam 64MB.

## Installation

### Global packages
```
# Install updates
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev
```

### Python dependencies
To install dependencies:
```
# For some reasons, the gphoto2-cffi library is not avaiable on pip, we must build it from sources
pip3 install -r requirements.txt
```

### Customize Pi
```
# Change bootscreen
wget https://github.com/IArchi/py-photobooth-simple/blob/main/doc/splash.png?raw=true
sudo cp splash.png /usr/share/plymouth/themes/pix/splash.png
#sudo plymouth-set-default-theme --rebuild-initrd pix

# Hide mouse 
echo "autohide = true" >> .config/wf-panel-pi.ini
echo "autohide_duration = 500" >> .config/wf-panel-pi.ini
echo "layer = top" >> .config/wf-panel-pi.ini

# Hide taskbar
sudo sed -i 's/^@lxpanel --profile LXDE-pi/#@lxpanel --profile LXDE-pi/' /etc/xdg/lxsession/LXDE-pi/autostart
sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini

sudo reboot
```

### Install ArduCAM (Only if you plan to use one)

Camera is expected to be connected to port CAM1.

```
# Declare camera
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt
sudo sh -c "echo 'dtoverlay=arducam-64mp,cam1' >> /boot/firmware/config.txt"

# Install drivers
sudo apt install -y raspberrypi-kernel raspberrypi-kernel-headers
sudo reboot
```

Run `uname -r` to find out which kernel version is installed on Pi 5.

If version is 6.6.28 or before, run:
```
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
./install_pivariety_pkgs.sh -p libcamera_apps
./install_pivariety_pkgs.sh -p 64mp_pi_hawk_eye_kernel_driver
sudo dpkg -i libcamera*.deb
sudo dpkg -i rpicam-apps*deb
rm libcamera* install_pivariety_pkgs.sh packages.txt rpicam-apps_1.4.4-2_arm64.deb 64mp_pi_hawk_eye_kernel_driver_links.txt
sudo apt -y update && sudo apt -y upgrade

# Reboot
sudo reboot
```

Otherwise, run:
```
uname -r # 6.6.31-v8-16k+

# Rollback to 6.6.28 (https://github.com/raspberrypi/rpi-firmware/commits/master/)
sudo rpi-update 1a47eacfe05acf3a7c1d8602c28c0ad2b4ffd315
sudo reboot

uname -r # 6.6.28-v8-16k+

# Download firmware
wget https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/Arducam_pivariety_v4l2_v1.0/arducam_64mp_kernel_driver_6.6.28.tar.gz
tar -zxvf arducam_64mp_kernel_driver_6.6.28.tar.gz Release/ && cd Release/

# Install PDAF firmware
sudo install -p -m 644 ./bin/6.6.28-v8-16k/arducam_64mp.ko.xz /lib/modules/6.6.28-v8-16k+/kernel/drivers/media/i2c/
sudo /sbin/depmod -a $(uname -r)
sudo reboot
```

To test camera:
```
libcamera-still --list-camera
libcamera-still --autofocus-mode=auto -f -o test.jpg
```

### Install Raspberry Camera Module V3 (Only if you plan to use one)

Camera is expected to be connected to port CAM0.

```
# Declare camera
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/ddtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt
sudo sh -c "echo 'dtoverlay=imx708,cam0' >> /boot/firmware/config.txt"

# Reboot
sudo reboot

# Test
libcamera-still --list-camera
libcamera-still --autofocus-mode=auto -f -o test.jpg
```

### Gphoto2 (Only if you plan to use a DSLR)
Gphoto2 should be fixed before use:
```
# Install required packages
pip3 install git+https://github.com/jbaiter/gphoto2-cffi.git --break-system-packages
sudo apt install -y snapd
sudo snap install core
sudo snap install gphoto2
sudo chmod -x /usr/lib/gvfs/gvfs-gphoto2-volume-monitor
sudo chmod -x /usr/lib/gvfs/gvfsd-gphoto2

# Test
gphoto2 --capture-image
```

### CUPS printer (Only if you plan to print collages)
```
# Install CUPS
sudo apt-get install -y cups cups-bsd python3-cups
sudo usermod -a -G lpadmin $USER
sudo cupsctl --remote-admin --remote-any

# Install Driverless printers
sudo apt install -y ipp-usb
sudo systemctl start ipp-usb.service

# Restart CUPS
sudo /etc/init.d/cups restart
```

Then go to `http://<raspberry-ip>:631/admin/` and declare a new printer.

### Led ring (Only if you plan to install one)
```
# Enable SPI on RaspberryPi
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
```

### Install kiosk mode (Pi Only)
```
# Install Kiosk & autostart
echo '[autostart]' >> .config/wayfire.ini
echo 'photobooth = /home/pi/photobooth.sh' >> .config/wayfire.ini

# Create runner
echo '#!/bin/bash' > /home/pi/photobooth.sh
echo 'cd /home/pi/' >> /home/pi/photobooth.sh
echo 'python3 photoboothapp.py' >> /home/pi/photobooth.sh
chmod +x photobooth.sh

# TODO : Disable desktop and buttons
```

### Run
To start the application:
```
python3 photoboothapp.py
```

## Customization
To customize collages, you can edit `logo.png`. As a PNG file, you can use transparency.

You can also edit `photoboothapp.py` to change some parameters such as:
 - LOCALES = Locales.get_EN (To select language to use among EN and FR)
 - FULLSCREEN = False (If set to True, the window fill take all available space)
 - COUNTDOWN = 3 (Countdown before the photo is taken)
 - ROOT_DIRECTORY = './DCIM' (Directory in which the photos and collages are stored)
 - PRINTER = 'truc' (The printer's name in CUPS)

## USB dump
A dedicated thread will handle USB dongles and automatically dump the whole content of the `ROOT_DIRECTORY` to the device.
Application will not be usable during the copy process but will display a message.

## TODO
 - Test with gphoto2
 - Fix piCamera2
