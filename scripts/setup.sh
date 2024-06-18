#!/bin/bash

echo 'Arducam should be plugged on slot #0'
read -p "Press [Enter] key to install ..."

# Enable Pi overlays
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
sudo sh -c "echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt"

# Update system packages
sudo apt update

# Install arducam 64Mp camera
./arducam_driver.sh
#sudo reboot

# Test camera
#libcamera-still --list-camera

# Install dependencies
sudo apt-get install -y gcc make build-essential git scons swig
sudo apt install -y ffmpeg libturbojpeg0 python3-pip libgl1 libgphoto2-dev

# Hide mouse
echo "autohide = true" >> .config/wf-panel-pi.ini
echo "autohide_duration = 500" >> .config/wf-panel-pi.ini
echo "layer = top" >> .config/wf-panel-pi.ini

# Hide taskbar
sudo sed -i '/^[^#].*wfrespawn wf-panel-pi/ s/^/# /' /etc/wayfire/defaults.ini

# Disable power warning
echo "avoid_warnings=1" | sudo tee -a /boot/config.txt && sudo apt remove lxplug-ptbatt -y

# Install CUPS
sudo apt-get install -y cups cups-bsd python3-cups
sudo usermod -a -G lpadmin $USER
sudo cupsctl --remote-admin --remote-any
sudo apt install -y ipp-usb
sudo systemctl start ipp-usb.service
sudo /etc/init.d/cups restart

# Install gphoto2
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/.env
chmod +x gphoto2-updater.sh
sudo ./gphoto2-updater.sh -s
rm gphoto2-updater.sh .env
pip3 install git+https://github.com/jbaiter/gphoto2-cffi.git --break-system-packages
sudo chmod -x /usr/lib/gvfs/gvfs-gphoto2-volume-monitor
sudo chmod -x /usr/lib/gvfs/gvfsd-gphoto2

# Disable media dialog
sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/LXDE-pi/pcmanfm.conf
sudo sed -i -e 's/autorun=1/autorun=0/g' /etc/xdg/pcmanfm/default/pcmanfm.conf

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
pip3 install -r requirements.txt --break-system-packages

# Autostart app
echo '[autostart]' >> .config/wayfire.ini
echo 'photobooth = /home/pi/photobooth.sh' >> .config/wayfire.ini
echo '#!/bin/bash' > /home/pi/photobooth.sh
echo 'cd /home/pi/' >> /home/pi/photobooth.sh
echo 'python3 photoboothapp.py' >> /home/pi/photobooth.sh
chmod +x photobooth.sh

# Reboot device
sudo reboot