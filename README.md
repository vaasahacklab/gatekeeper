# Gatekeeper
Raspberry Pi + GSM Shield + python to control lock and environment

Lock system for Vaasa Hacklab to let members in and doorbell for visitors

## Installation
First install Raspbian Jessie from https://github.com/debian-pi/raspbian-ua-netinst (I used 1.1.x, shouldn't matter too much as long Jessie is being installed and then upgraded to Stretch).

SSH into raspberry as root, password: raspbian

```
ssh root@<IP-address>
```

Then let's install basic tools, configure system basics, upgrade to Stretch

```
apt-get update && apt-get upgrade && apt-get dist-upgrade
apt-get install -y raspi-config raspi-copies-and-fills locales tzdata nano git bash-completion sudo
dpkg-reconfigure locales # Choose appropriate locales and timezone for you, usually en_US.UTF-8 and some local one, for system default I recommend en_US.UTF-8
dpkg-reconfigure tzdata
sed -i 's/jessie/stretch/g' /etc/apt/sources.list
sed -i 's/jessie/stretch/g' /etc/apt/sources.list.d/raspberrypi.org.list
apt-get update && apt-get upgrade && apt-get dist-upgrade
reboot
```


After reboot, SSH back in

```
ssh root@<IP-address>
```

Continue setupping

```
apt-get --purge -y autoremove
apt-get install -y python3 python3-venv python3-dev build-essential libssl-dev libffi-dev raspberrypi-sys-mods
```

Create user for running Gatekeeper, no admin privileges

```
groupadd gpio
groupadd spi
useradd -c "Vaasa Hacklab Gatekeeper" -U -m -d /home/gatekeeper -s /bin/bash -G dialout,gpio,spi gatekeeper
passwd gatekeeper
```

Give user privileges to access GPIO without root

```
sudo chown root.gpio /dev/gpiomem
sudo chmod g+rw /dev/gpiomem
```

## Remove tty and logging from serialport
```
remove references to /dev/ttyAMA0 from /boot/cmdline.txt - which sets up the serial console on boot.
```

disable the getty on that serial port in /etc/inittab, Comment out the following line:

```
T0:23:respawn:/sbin/getty -L ttyAMA0 115200 vt100
```

Run these:
```
systemctl stop serial-getty@ttyAMA0.service
systemctl disable serial-getty@ttyAMA0.service
exit
```

Enable SPI: Add this line into /boot/config.txt
```
dtparam=spi=on
```

Setup logfile

```
touch /var/log/gatekeeper/gatekeeper.log
touch /var/log/gatekeeper/audit.log
chown gatekeeper:gatekeeper /var/log/gatekeeper/gatekeeper.log
chown gatekeeper:gatekeeper /var/log/gatekeeper/audit.log
```

Exit user root SSH-session

```
exit
```

## Login with user gatekeeper
```
ssh gatekeeper@<ip-address>
```

Fetch and setup Gatekeeper

```
git clone https://github.com/vaasahacklab/gatekeeper.git
cd gatekeeper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/lthiery/SPI-Py.git
cd SPI-Py
python setup.py install
cd ..
```

copy config example to config and edit it according to your needs

```
cp config.json.example config.json
nano config.json
```

Exit user gatekeeper SSH-session

```
exit
```

## Login again with root

```
ssh root@<IP-address>
```

Copy gatekeeper systemd service -file into systemd and enable it

```
cp /home/gatekeeper/gatekeeper/gatekeeper.service.example /lib/systemd/system/gatekeeper.service
systemctl daemon-reload
systemctl enable gatekeeper.service
exit
```

## Optional

Highly recommended is to also add sudo user for maintenance, not for public usage, and disable root login:

SSH into raspberry as root, password: raspbian

```
ssh root@<IP-address>
```

Generate new user for admin things:

```
useradd -c "Vaasa Hacklab" -d /home/hacklab -m -s /bin/bash -U -G sudo hacklab
passwd hacklab
exit
```

then ssh with new user:

```
ssh hacklab@<IP-address>
```

then run to disable root login:

```
sudo passwd -l root
exit
```
