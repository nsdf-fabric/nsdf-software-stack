# Instrutions

```
sudo apt install -y xrdp
# sudo systemctl status xrdp
sudo adduser xrdp ssl-cert
sudo systemctl restart xrdp

# check port is open 3389


# comment these lines 
# sudo nano /etc/xrdp/startwm.sh
#   test -x /etc/X11/Xsession && exec /etc/X11/Xsession
#   exec /bin/sh /etc/X11/Xsession
# and add
#   startxfce4

# had problem with nvidia drivers == they are not recognized
```