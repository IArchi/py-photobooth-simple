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
sudo apt update
sudo apt upgrade -y

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

### Install ArduCAM (Only if you plan to use one)
```
# Declare camera
sudo sh -c "echo 'dtoverlay=arducam-64mp' >> /boot/firmware/config.txt"

# Install drivers
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
./install_pivariety_pkgs.sh -p libcamera_apps
sudo dpkg -i libcamera*.deb
sudo dpkg -i rpicam-apps*deb
rm libcamera* install_pivariety_pkgs.sh packages.txt rpicam-apps_1.4.4-2_arm64.deb

# Reboot
sudo reboot

# Test
libcamera-hello
libcamera-vid -t 0 --autofocus-mode auto --vflip 1
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
sudo apt install cups -y
TODO
```

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
