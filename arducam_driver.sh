#!/bin/bash

CONFIG_FILE_NAME=packages.txt
CONFIG_FILE_DOWNLOAD_LINK=https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/packages.txt

RED='\033[0;31m'
GREEN="\[\033[0;32m\]"
NC='\033[0m' # No Color

rev=$(cat /proc/cpuinfo | grep Revision | awk '{print substr($NF,length($NF)-5,6)}')
kernel=$(uname -r)
code_name=$(awk -F"[)(]+" '/VERSION=/ {print $2}' /etc/os-release)
$(dpkg-architecture -earm64)
if [ $? == 0 ]; then
    code_name=$code_name"-arm64"
fi
arch=$(arch)
echo "================================================="
echo "Hardware Revision: ${rev}"
echo "Kernel Version: ${kernel}"
echo "OS Codename: ${code_name}"
echo "ARCH: ${arch}"
echo "================================================="
echo ""

rm -rf install/
mkdir -p install
cd install

# Download packages list
rm -f $CONFIG_FILE_NAME
wget -O $CONFIG_FILE_NAME $CONFIG_FILE_DOWNLOAD_LINK
source $CONFIG_FILE_NAME
echo "Supported packages:"
for key in ${!package_cfg_names[*]};do
echo -e "\t$key"
done
echo ""

# Install libcamera
package='libcamera_bookworm'
package_cfg_name=${package_cfg_names[$package]}
package_cfg_download_link=${package_cfg_download_links[$package]}
if [[ (-z $package_cfg_name) || (-z $package_cfg_download_link) ]]; then
        echo -e "${RED}Unsupported package ${package}.${NC}"
        echo ""
        exit -1
fi
echo -e "${GREEN}Package ${package} found !${NC}"
rm -rf $package_cfg_name
wget -O $package_cfg_name $package_cfg_download_link
source $package_cfg_name
download_link=${package_download_links[$code_name]}
pkg_name=${package_names[$code_name]}
rm -rf $pkg_name
wget -O $pkg_name $download_link
echo -e "${GREEN}Install package ${pkg_name}${NC}"
sudo apt purge libpisp0.0.1 -y
sudo apt install libpisp-dev -y
sudo apt --reinstall install -y ./$pkg_name
pkg_name_dev=$(echo "$pkg_name" | sed 's/[0-9]\+\.[0-9]\+/-dev/')
download_link_dev=$(echo "$download_link" | sed 's/\([0-9]\+\.[0-9]\+\)_/-dev_/')
pkg_name_ipa=$(echo "$pkg_name" | sed 's/[0-9]\+\.[0-9]\+/-ipa/')
download_link_ipa=$(echo "$download_link" | sed 's/\([0-9]\+\.[0-9]\+\)_/-ipa_/')
wget -O $pkg_name_dev $download_link_dev
wget -O $pkg_name_ipa $download_link_ipa
echo -e "${GREEN}Install package ${pkg_name_dev}${NC}"
sudo apt --reinstall install -y ./$pkg_name_dev
echo -e "${GREEN}Install package ${pkg_name_ipa}${NC}"
sudo apt --reinstall install -y ./$pkg_name_ipa
echo -e "${GREEN}Install Python dependencies.${NC}"
sudo apt install -y python3-libcamera
sudo apt install -y python3-picamera2

# Install libcamera_apps
package='libcamera_apps_bookworm'
package_cfg_name=${package_cfg_names[$package]}
package_cfg_download_link=${package_cfg_download_links[$package]}
if [[ (-z $package_cfg_name) || (-z $package_cfg_download_link) ]]; then
        echo -e "${RED}Unsupported package ${package}.${NC}"
        echo ""
        exit -1
fi
echo -e "${GREEN}Package ${package} found !${NC}"
rm -rf $package_cfg_name
wget -O $package_cfg_name $package_cfg_download_link
source $package_cfg_name
download_link=${package_download_links[$code_name]}
pkg_name=${package_names[$code_name]}
rm -rf $pkg_name
wget -O $pkg_name $download_link
echo -e "${GREEN}Install package ${pkg_name}${NC}"
sudo apt --reinstall install -y ./$pkg_name

# Retrieve driver download links
package='64mp_pi_hawk_eye_kernel_driver'
package_cfg_name=${package_cfg_names[$package]}
package_cfg_download_link=${package_cfg_download_links[$package]}
if [[ (-z $package_cfg_name) || (-z $package_cfg_download_link) ]]; then
        echo -e "${RED}Unsupported package ${package}.${NC}"
        echo ""
        exit -1
fi
echo -e "${GREEN}Package ${package} found !${NC}"
rm -rf $package_cfg_name
wget -O $package_cfg_name $package_cfg_download_link
source $package_cfg_name

# Identify driver for current kernel version
kernel_version=$(uname -r | grep -oP '\d+\.\d+\.\d+')
pkg_name=${package_names[$kernel_version]}
download_link=${package_download_links[$kernel_version]}
if [[ (-z $pkg_name) || (-z $download_link) ]]; then
        echo -e "${RED}Unsupported kernel.${NC}"
        echo ""
        exit -1
fi
echo -e "${GREEN}Package ${package} for kernel ${kernel_version} found !${NC}"
rm -rf $pkg_name
wget -O $pkg_name $download_link

# Extract driver
tar -zxvf $pkg_name Release/

# Identify subversion
if [[ $kernel == *"2712"* ]] || [[ $kernel == *"16k"* ]]; then
    version=$kernel_version"-v8-16k"
elif [[ $kernel == *"v8"* ]]; then
    version=$kernel_version"-v8"
elif [[ $kernel == *"v7l"* ]]; then
    version=$kernel_version"-v7l"
elif [[ $kernel == *"v7"* ]]; then
    version=$kernel_version"-v7"
elif [[ $kernel == *"v6"* ]]; then
    version=$kernel_version
fi

driver_file="Release/bin/${version}/arducam_64mp.ko.xz"
if [ ! -f "$driver_file" ]; then
        echo -e "${RED}Cannot find compatible driver for kernel ${version}${NC}"
        exit -1
fi

echo -e "${GREEN}Driver found !${NC}"

# Install version
sudo install -p -m 644 $driver_file /lib/modules/$(uname -r)/kernel/drivers/media/i2c/
sudo /sbin/depmod -a $(uname -r)

# Declare camera in configuration
sudo sed -i 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-kms-v3d,cma-512/' /boot/firmware/config.txt
sudo sh -c "echo 'dtoverlay=arducam-64mp,cam0' >> /boot/firmware/config.txt"

echo -e "${GREEN}Success${NC}"

cd .. && rm -rf install/

# List connected cameras (a reboot might be required)
libcamera-still --list-camera