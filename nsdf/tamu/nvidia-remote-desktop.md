


# FluidStack  (RTX A6000) no display manager, simplest version 

See
- https://dugas.ch/lord_of_the_files/run_your_unity_ml_executable_in_the_cloud.html
- nvidia drivers are already installed

```

function KillAll() { 
   for it in $@ ; do 
      for id in $(sudo ps aux | grep -i $1  | grep -v grep | awk '{print $2}'); do
         sudo kill -9 $id
      done
   done
}

sudo su -

sed -i "/^[^#]*PasswordAuthentication[[:space:]]no/c\PasswordAuthentication yes" /etc/ssh/sshd_config
ufw disable

# solve problem with cuda signature
apt-key del 7fa2af80 || true
apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/$(uname -m)/3bf863cc.pub || true
apt update

systemctl isolate multi-user.target

# I am using existing drivers
nvidia-xconfig --use-display-device=none --virtual=1600x900 --preserve-busid --enable-all-gpus

# start Xorg with nvidia drivers
nohup Xorg :0 &
ps aux | grep Xorg  | grep -v grep
cat /etc/X11/xorg.conf | grep -i "driver" # # you should see nvidia
apt install -y mesa-utils
DISPLAY=:0 glxinfo | grep version # you should see something like NVIDIA XXX.YY.ZZ
nvidia-smi  # xorg should show up in the running programs

DEBIAN_FRONTEND=noninteractive apt install -y xfce4 

export DISPLAY=:0
nohup startxfce4 &

# install nomachine (xrdp and chome remote desktop not works)
wget https://download.nomachine.com/download/7.7/Linux/nomachine_7.7.4_1_amd64.deb -O nomachine.deb
apt install -y -f ./nomachine.deb
# sudo /usr/NX/bin/nxserver --restart

echo "$(curl ifconfig.me)"

# now you connect client-side using nomachine and do this
# you will see NVIDIA DRIVER
# glxinfo | grep -i "opengl.*version"

exit
```

# AWS EC2 `g4dn.xlarge`  instance Tesla T4 (headless) - Ubuntu 20

```
sudo passwd $USER
sudo sed -i "/^[^#]*PasswordAuthentication[[:space:]]no/c\PasswordAuthentication yes" /etc/ssh/sshd_config
sudo ufw disable

sudo apt update
sudo apt install -y \
  curl git wget vim nano cmake swig build-essential less bzip2 \
   zip unzip pkg-config tasksel

sudo systemctl isolate multi-user.target
sudo tasksel install ubuntu-desktop
sudo apt install -y gdm3

# output must be `/usr/sbin/gdm3` 
# otherwise run `sudo dpkg-reconfigure gdm3`
cat /etc/X11/default-display-manager 

sudo apt upgrade -y
sudo reboot

# set Wayland Enable to false.
sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf 
sudo systemctl restart gdm3

# check the output is `graphical.target`
# otherwise run `sudo systemctl set-default graphical.target
sudo systemctl get-default

#  in graphical.target NoMachine shares the existing Xorg display
sudo systemctl isolate graphical.target

# verify X is running
ps aux | grep X | grep -v grep

# install nvidia drivers
# - https://www.nvidia.it/Download/index.aspx?lang=it
# - https://browser.geekbench.com/cuda-benchmarks

# g4dn.xlarge is Tesla T4 driver 510
sudo lshw -c video

sudo dpkg --add-architecture i386

sudo apt update
sudo apt install -y \
   libc6:i386 \
   libglvnd-dev \
   mesa-utils \
   linux-headers-$(uname -r)

# Testa T4 (change as needed depending on your graphic card)
wget https://us.download.nvidia.com/tesla/510.47.03/NVIDIA-Linux-x86_64-510.47.03.run -O install-nvidia-drivers.run
sudo sh install-nvidia-drivers.run

sudo nvidia-xconfig  --enable-all-gpus --preserve-busid

# you should see nvidia
cat /etc/X11/xorg.conf | grep -i "driver"

sudo systemctl restart gdm3
sudo systemctl status gdm.service

# you should see `/usr/lib/xorg/Xorg` and `/usr/bin/gnome-shell` at the bottom
nvidia-smi

# this is the proof opengl is working
# example: `OpenGL version string: 4.6.0 NVIDIA 510.47.03`
XAUTHORITY=$(ps aux | grep "X.*\-auth" | grep -v grep | sed -n 's/.*-auth \([^ ]\+\).*/\1/p')
echo $XAUTHORITY
sudo DISPLAY=:0 XAUTHORITY=$XAUTHORITY glxinfo | grep -i "opengl.*version"

wget https://download.nomachine.com/download/7.7/Linux/nomachine_7.7.4_1_amd64.deb -O nomachine.deb
sudo apt install -y -f ./nomachine.deb
# sudo rm  /usr/NX/var/log/*.log
# sudo /usr/NX/bin/nxserver --restart
# sudo more  /usr/NX/var/log/*.log
# sudo vi /usr/NX/etc/server.cfg 



# sudo /usr/NX/bin/nxserver --shutdown

# get your public ip
curl ifconfig.me

# now you connect client-side using nomachine and do this
# you will see NVIDIA DRIVER
# glxinfo | grep -i "opengl.*version"

```
