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
The application is compatible with [piCamera module 3](https://www.raspberrypi.com/products/camera-module-3/), DSLR and CV2 devices.
By default, it will try to use the best available quality:
 - If piCamera is connected, it will be used for preview ;
 - If DSLR is connected, it will be used for capture ;

If one of these is not available, it will use the first available one.

## Compatibility
Tested on MacOs Sonoma/Sequoia and RaspberryPi 5 8GB with Pi Camera module 3.

## Materials
| Product                              | Links                                                                                                             |
|--------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| Raspberry Pi 5                       | https://www.raspberrypi.com/products/raspberry-pi-5/                                                              |
| Pi camera module 3                   | https://www.raspberrypi.com/products/camera-module-3/                                                             |
| Led Ring 5V - 12 bits                | https://www.az-delivery.de/en/products/rgb-led-ring-ws2812-mit-12-rgb-leds-5v-fuer-arduino?variant=18912609108064 |
| DNP DS620 printer                    | https://www.dnpphoto.eu/en/product-range/photo-printers/item/120-ds620                                            |
| Canon EOS 2000D (EU) / Rebel T7 (US) | https://global.canon/en/c-museum/product/dslr873.html                                                             |
| Ingcool 7" touchscreen               | http://www.ingcool.com/wiki/7DP-CAPLCD                                                                            |
| Godox Flash MS300V                   | https://store.godox.eu/en/flash-lamps/5732-godox-ms300-v-studio-flash-6952344225646.html                          |
| Godox BDR-W420 Beauty Dish 42cm      | https://store.godox.eu/en/beauty-dish/101-godox-bdr-w420-beauty-dish-420mm-white-bounce-6952344206126.html        |
| Pixel TF-321 Hot Shoe                |                                                                                                                   |

## Installation

### Global packages
```
# Install updates
sudo apt update

# Install dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev

#Install Python dependencies
pip3 install -r requirements.txt --break-system-packages
```

### Customize Pi and enable Kiosk mode
```
# Hide mouse and panel
sudo sed -i 's/\[autostart\]/\[autostart]\r\background = wf-background/g /etc/wayfire/defaults.ini

# Hide taskbar
#sudo sed -i 's/^@lxpanel --profile LXDE-pi/#@lxpanel --profile LXDE-pi/' /etc/xdg/lxsession/LXDE-pi/autostart
sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini

# Disable power warning
echo "avoid_warnings=1" | sudo tee -a /boot/firmware/config.txt && sudo apt remove lxplug-ptbatt -y

# Disable media mount dialog
sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/LXDE-pi/pcmanfm.conf
sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/default/pcmanfm.conf

sudo reboot
```

### Install Ingcool 7" touchscreen (If it's the one you use)
```
sudo sh -c "echo '# Ingcool 7in touch screen' >> /boot/firmware/config.txt"
sudo sh -c "echo 'max_usb_current=1' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_group=2' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_mode=87' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_cvt 1024 600 60 6 0 0 0' >> /boot/firmware/config.txt"
sudo sh -c "echo 'hdmi_drive=1' >> /boot/firmware/config.txt"
sudo sh -c "echo '' >> /boot/firmware/config.txt"
```

### Install Raspberry Camera Module V3 (Only if you plan to use one. Highly suggested)

```
# Allocate more memory
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt

# Enable camera
sudo sh -c "echo '# Camera module 3' >> /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=imx708,cam0' >> /boot/firmware/config.txt"
sudo sh -c "echo '' >> /boot/firmware/config.txt"


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
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/.env
chmod +x gphoto2-updater.sh
sudo ./gphoto2-updater.sh -s
rm gphoto2-updater.sh .env

# Fix for USB not available
sudo chmod -x /usr/lib/gvfs/gvfs-gphoto2-volume-monitor
sudo chmod -x /usr/lib/gvfs/gvfsd-gphoto2

# Test
gphoto2 --capture-image
```

### CUPS printer (Only if you plan to print collages)
```
# Install CUPS
sudo apt-get install -y cups libcups2-dev python3-cups
sudo usermod -a -G lpadmin $USER
sudo cupsctl --remote-admin --remote-any

# Install Driverless printers
sudo apt install -y printer-driver-gutenprint

# Restart CUPS
sudo /etc/init.d/cups restart
```

 - Connect the printer through USB ;
 - Go to `https://<raspberry-ip>:631/admin/` ;
 - Declare a new printer (credentials are the ones to connect to SSH) ;
 - Name it `DS620` (Accordingly to your `config.ini`);
 - Select DNP brand and DS620 model.

### Led ring (Only if you plan to install one)
```
# Enable SPI on RaspberryPi
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt

# Install Python dependency
pip3 install spidev --break-system-packages
```

Connect WS2812 Ring led on the following GPIO pins:
| WS2812 pins | Raspberry Pi pins              |
|-------------|--------------------------------|
| GND         | 6, 9, 14, 20, 25 (GND)         |
| DIN         | MOSI, Pin 19, GPIO 10          |
| VCC         | 5V. At least one of pin 2 or 4 |

### Autostart photobooth on boot
```
echo '[autostart]' >> ~/.config/wayfire.ini
echo 'photobooth = /home/pi/photobooth.sh' >> ~/.config/wayfire.ini
echo '#!/bin/bash' > /home/pi/photobooth.sh
echo 'cd /home/pi/photobooth/' >> /home/pi/photobooth.sh
echo 'python3 photoboothapp.py' >> /home/pi/photobooth.sh
chmod +x /home/pi/photobooth.sh
```

### Run
To start the application:
```
python3 photoboothapp.py
```

## Customization
You can also edit `config.ini` to change some parameters such as:
 - Autorestart on failure ;
 - Full screen window ;
 - Countdown before the photo is taken ;
 - Directory in which the photos and collages are stored ;
 - Printer's name in CUPS ;
 - Calibration matrix if using hybrid mode (DSLR + piCamera or DSLR + webcam) ;
 - Overlay to use.

## USB dump
A dedicated thread will handle USB dongles and automatically dump the whole content of the `DCIM_DIRECTORY` to the device.
Application will not be usable during the copy process but will display a message.

**USB dongle must be formated to FAT-32.**

## TODO
 - Gradient progress bar ?
 - Better success screen
 - position of print button (too low)
