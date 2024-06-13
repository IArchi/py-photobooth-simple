#!/bin/bash

echo 'Arducam should be plugged on slot #1'
read -p "Press [Enter] key to install ..."

# Enable Pi overlays
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt
sudo sh -c "echo 'dtoverlay=imx708' >> /boot/firmware/config.txt"
sudo sh -c "echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt"

# Update system packages
sudo apt update && sudo apt upgrade -y
sudo reboot

# Test camera
libcamera-still --list-camera

# Install dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev

# Boot screen
sudo cp splash.png /usr/share/plymouth/themes/pix/splash.png
sudo sed -i 's/console=tty1/console=tty3/' /boot/firmware/cmdline.txt

# Hide mouse 
echo "autohide = true" >> .config/wf-panel-pi.ini
echo "autohide_duration = 500" >> .config/wf-panel-pi.ini
echo "layer = top" >> .config/wf-panel-pi.ini

# Hide taskbar
sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini

# Install gphoto2
pip3 install git+https://github.com/jbaiter/gphoto2-cffi.git --break-system-packages

# Install CUPS
sudo apt-get install -y cups cups-bsd python3-cups
sudo usermod -a -G lpadmin $USER
sudo cupsctl --remote-admin --remote-any
sudo apt install -y ipp-usb
sudo systemctl start ipp-usb.service
sudo /etc/init.d/cups restart


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
