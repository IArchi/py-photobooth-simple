#!/bin/bash

echo 'Arducam should be plugged on slot #1'
read -p "Press [Enter] key to install ..."

# Enable Pi overlays
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt
sudo sh -c "echo 'dtoverlay=arducam-64mp,cam1' >> /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt"

# Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y raspberrypi-kernel raspberrypi-kernel-headers
sudo reboot

# Rollback kernel to 6.6.28 (https://github.com/raspberrypi/rpi-firmware/commits/master/)
sudo rpi-update 1a47eacfe05acf3a7c1d8602c28c0ad2b4ffd315

# Download and install firmware
wget https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/Arducam_pivariety_v4l2_v1.0/arducam_64mp_kernel_driver_6.6.28.tar.gz
tar -zxvf arducam_64mp_kernel_driver_6.6.28.tar.gz Release/ && cd Release/
sudo install -p -m 644 ./bin/6.6.28-v8-16k/arducam_64mp.ko.xz /lib/modules/6.6.28-v8-16k+/kernel/drivers/media/i2c/
sudo /sbin/depmod -a $(uname -r)
cd .. && rm -rf Release/
sudo reboot

# Test camera
libcamera-still --list-camera

# Install dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt -y install ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev fonts-noto-color-emoji rclone inotify-tools

# Add GitHub ssh key
ssh-keygen -t ed25519 -C "#@#.com"
eval "$(ssh-agent -s)"
echo "Host github.com" >> ~/.ssh/config
echo "  AddKeysToAgent yes" >> ~/.ssh/config
echo "  IdentityFile ~/.ssh/id_ed25519" >> ~/.ssh/config

echo 'Connect to Github and add the following key to SSH tab'
# Add to settings
cat ~/.ssh/id_ed25519.pub
read -p "Press [Enter] when done ..."
ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

# Download photobooth
git clone git@github.com:IArchi/py-photobooth-simple.git photobooth
cd photobooth
pip3 install git+https://github.com/jbaiter/gphoto2-cffi.git --break-system-packages
pip3 install -r requirements.txt --break-system-packages

# Install Kiosk & autostart
sudo apt install wtype -y
echo '[autostart]' >> .config/wayfire.ini
echo 'photobooth = /home/pi/photobooth.sh' >> .config/wayfire.ini

# Create runner
echo '#!/bin/bash' > /home/pi/photobooth.sh
echo 'cd /home/pi/' >> /home/pi/photobooth.sh
echo 'python3 photoboothapp.py' >> /home/pi/photobooth.sh
chmod +x photobooth.sh
