# Gatekeeper #
Raspberry Pi + GSM Shield + python to control lock and environment

Lock system for Vaasa Hacklab to let members in and doorbell for visitors

# Physical #
## Stalli door locking mechanism wiring

DB-9 connector:

```
+-------------+
 \ 1 2 3 4 5 /
  \ 6 7 8 9 S
   +-------+
```

Lock mechanic internal wiring, current setup:

Male DB-9 connector at chassis, all wires soldered at connector inside chassis:


```
1: Power positive to lock solenoid (+24V), 1.5mm²
2: Power negative to lock solenoid (+24V), 1.5mm²
3: Latch open indicator (C, NC, NO) (not installed currently)
4: Latch open indicator (C, NC, NO) (not installed currently)
5: Latch open indicator (C, NC, NO) (not installed currently)
S: Chassis/shielding ground, not entirely neccesary, recommended, we used 2.5mm² wire inside chassis
```

Cable:

Pins 1&2 are for power, wires they use can be separate wires as they need to be relateively thick (0.5mm² minimum, preferably more, we used 1.5mm²) in comparison to rest of pins (3-9) which are logic level signals which can be much anything in size, we used shielded CAT 5e patch cable)

Cable setup is straight DB-9 male to DB-9 female pin to pin cable, we used following schema:

```
-- Separate 2x1.5mm² cable --
1: 1.5mm² black
2: 1.5mm² blue
S: Shielding drain wire

```

# Software
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
apt-get --purge autoremove
apt-get install python2.7 python-pip build-essential libssl-dev libffi-dev raspberrypi-sys-mods
pip2 install virtualenv
```

Create user for running Gatekeeper, no admin privileges

```
groupadd gpio
groupadd spi
useradd -c "Vaasa Hacklab Gatekeeper" -U -m -d /home/gatekeeper -s /bin/bash -G dialout,gpio,spi gatekeeper
passwd gatekeeper
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
touch /var/log/gatekeeper.log
chown gatekeeper:gatekeeper /var/log/gatekeeper.log
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
mkdir venv
virtualenv venv
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
cp /home/gatekeeper/gatekeeper/gatekeeper.service /lib/systemd/system/gatekeeper.service
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
