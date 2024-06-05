#!/bin/bash

echo 'Camera should be plugged on slot #1'
read -p "Press [Enter] key to install ..."

sudo sed -i 's/^# dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=arducam-64mp' >> /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt"

# Update system
sudo apt update
sudo apt upgrade -y

# Install camera driver
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
./install_pivariety_pkgs.sh -p libcamera_apps
sudo dpkg -i libcamera*.deb
sudo dpkg -i rpicam-apps*deb

# Test camera
libcamera-hello

rm libcamera* install_pivariety_pkgs.sh packages.txt rpicam-apps_1.4.4-2_arm64.deb 

# Install dependencies
sudo apt -y install ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev fonts-noto-color-emoji rclone inotify-tools
pip3 install opencv-contrib-python --break-system-packages
pip3 install rpi_ws281x adafruit-circuitpython-neopixel --break-system-packages

# Install LED ring
sudo apt-get install -y gcc make build-essential git scons swig

# Add GitHub ssh key
ssh-keygen -t ed25519 -C "#@#.com"
eval "$(ssh-agent -s)"
nano  ~/.ssh/config
 
Host github.com
  AddKeysToAgent yes
  IdentityFile ~/.ssh/id_ed25519

# Add to settings
cat ~/.ssh/id_ed25519.pub 

ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

# Download photobooth
git clone git@github.com:IArchi/py-photobooth-simple.git photobooth
cd photobooth
pip3 install git+https://github.com/jbaiter/gphoto2-cffi.git --break-system-packages
pip3 install -r requirements.txt --break-system-packages 


# Install Kiosk
sudo apt install wtype -y
sudo nano .config/wayfire.ini

[autostart]
photobooth = /home/pi/photobooth.sh

# Create runner
touch photobooth.sh && chmod +x photobooth.sh
nano photobooth.sh

#!/bin/bash
cd /home/pi/    
