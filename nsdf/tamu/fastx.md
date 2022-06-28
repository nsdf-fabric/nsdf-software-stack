# Instruction

Links:
- https://www.starnet.com/xwin32kb/fastx_2/
- https://www.starnet.com/xwin32kb/fastx-installation-instructions/
- https://www.starnet.com/xwin32kb/fastx-3-installation/
- https://www.starnet.com/download/fastx3.2?ID=1042281-6093
- https://www.chpc.utah.edu/documentation/software/fastx.php

```
wget https://www.starnet.com/files/private/FastX32/setup-fastx-server.sh
sudo bash setup-fastx-server.sh
sudo apt install -y fastx-server
sudo /usr/lib/fastx/3/install.sh
# DO YOU HAVE a SERVER LICENSE :no
more /var/fastx/license/*.lic
sudo /usr/lib/fastx/3/install/suggestions
sudo passwd ubuntu
https://54.224.148.221:3300/auth/ssh/

sudo service ssh restart

```