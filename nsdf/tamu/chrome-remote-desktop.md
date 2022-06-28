# Instructions

See:
- https://cloud.google.com/architecture/chrome-desktop-remote-on-compute-engine

IMPORTANT NOTE: chome will always use its Xorg.conf files so I didn't find a way
to enable NVIDIA drivers. Instead I am alwaying getting mesa. For this reason
it's not usable for a LINUX-Gpu-based remote machine

```
wget https://dl.google.com/linux/direct/chrome-remote-desktop_current_amd64.deb
sudo apt install -y ./chrome-remote-desktop_current_amd64.deb
rm -f chrome-remote-desktop_current_amd64.deb

# GNOME
sudo bash -c 'echo "exec /usr/bin/gnome-session" > /etc/chrome-remote-desktop-session'

# xfce
sudo bash -c 'echo "exec /etc/X11/Xsession /usr/bin/xfce4-session" > /etc/chrome-remote-desktop-session'

# - Goto https://remotedesktop.google.com/headless
# - Click "Authorize another computer"
# - Press "NEXT"
# - copy the line and run, then go to chrome remote display
# - Example of the generated line
# - DISPLAY= /opt/google/chrome-remote-desktop/start-host --code="XXXXX" --redirect-url="https://remotedesktop.google.com/_/oauthredirect" --name=$(hostname)
# code is 100200
sudo systemctl status chrome-remote-desktop@$USER
sudo passwd $USER #100200`


```