#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import serial               # Serial communication
import re                   # Regular expressions
import logging              # Hmm what could this be for?
import os                   # To call external stuff
import sys                  # System calls
import signal               # Catch kill signal
import time                 # For the sleep function
import select               # For select.error
from errno import EINTR     # Read interrupt
import RPi.GPIO as GPIO     # For using Raspberry Pi GPIO
import threading            # For enabling multitasking
import requests             # HTTP library
import json                 # JSON parser, for config file
from shutil import copyfile # File copying
import paramiko             # SSH access library
import paho.mqtt.publish as publish # MQTT door name logging
from pprint import pformat  # Pretty Print formatting

# Setup logging
LOG_FILENAME = '/var/log/gatekeeper.log'
FORMAT = "%(asctime)-12s: %(levelname)-8s - %(message)s"
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,format=FORMAT)
log = logging.getLogger("GateKeeper")

# Load configuration file
log.debug("Loading config file...")

try:
  with open(os.path.join(sys.path[0], 'config.json'), 'r') as f:
    config = json.load(f)
except Exception as e:
  log.debug('Failed loading config file: ' + str(e))
  raise e

log.debug("Config file loaded.")

# Setup GPIO output pins, GPIO.BOARD
modem_power = 11
modem_reset = 12
lock = 36
locklight = 37

# Setup GPIO input pins, GPIO.BOARD
latch = 29
button_open_lock = 38
switch_keep_lock_open = 40

# Setup modem data and control serial port settings (Todo: Make own python module for modem handling stuff?)
# Data port (Can be same or diffirent as command port)
data_port = '/dev/ttyAMA0'
data_baudrate = 115200
data_parity = serial.PARITY_ODD
data_stopbits = serial.STOPBITS_ONE
data_bytesize = serial.EIGHTBITS
data_xonxoff = True
data_rtscts = False
data_dsrdtr = False

# Command port (Can be same or diffirent as data port)
command_port = '/dev/ttyAMA0'
command_baudrate = 115200
command_parity = serial.PARITY_ODD
command_stopbits = serial.STOPBITS_ONE
command_bytesize = serial.EIGHTBITS
command_xonxoff = True
command_rtscts = False
command_dsrdtr = False

# Setup over, start defining classes
class Modem:
  linestatus_loop = False
  data_channel = serial.Serial(port=data_port,baudrate=data_baudrate,parity=data_parity,stopbits=data_stopbits,bytesize=data_bytesize,xonxoff=data_xonxoff,rtscts=data_rtscts,dsrdtr=data_dsrdtr,timeout=None,writeTimeout=1)

  def enable_caller_id(self):
    command_channel = serial.Serial(port=command_port,baudrate=command_baudrate,parity=command_parity,stopbits=command_stopbits,bytesize=command_bytesize,xonxoff=command_xonxoff,rtscts=command_rtscts,dsrdtr=command_dsrdtr,timeout=0,writeTimeout=1)
    command_channel.isOpen()
    command_channel.write("AT+CLIP=1" + "\r\n")
    command_channel.close()
    log.debug("Enabled caller ID")

  def hangup(self):
    command_channel = serial.Serial(port=command_port,baudrate=command_baudrate,parity=command_parity,stopbits=command_stopbits,bytesize=command_bytesize,xonxoff=command_xonxoff,rtscts=command_rtscts,dsrdtr=command_dsrdtr,timeout=0,writeTimeout=1)
    command_channel.isOpen()
    command_channel.write("AT+HVOIC" + "\r\n") # Disconnect only voice call (for example keep possible existing dataconnection online)
    command_channel.close()
    log.debug("We hung up")

  def power_on(self):
    command_channel = serial.Serial(port=command_port,baudrate=command_baudrate,parity=command_parity,stopbits=command_stopbits,bytesize=command_bytesize,xonxoff=command_xonxoff,rtscts=command_rtscts,dsrdtr=command_dsrdtr,timeout=0.2,writeTimeout=1)
    command_channel.isOpen()
    command_channel.write("AT"+"\r\n")
    command_channel.readline()
    buffer = command_channel.readline()
    if not buffer:
      log.debug("Powering on modem")
      GPIO.output(modem_power, GPIO.HIGH)
      while True:
        line = command_channel.readline().strip()
        if line == "RDY":
         log.debug("Modem powered on")
         break
      GPIO.output(modem_power, GPIO.LOW)
      log.debug("Waiting modem to be call ready")
      while True:
        line = command_channel.readline().strip()
        if line == "Call Ready":
         log.debug("Modem call ready")
         break
    else:
      log.debug("Modem already powered")

  def power_off(self):
    command_channel = serial.Serial(port=command_port,baudrate=command_baudrate,parity=command_parity,stopbits=command_stopbits,bytesize=command_bytesize,xonxoff=command_xonxoff,rtscts=command_rtscts,dsrdtr=command_dsrdtr,timeout=0.2,writeTimeout=1)
    command_channel.isOpen()
    command_channel.write("AT"+"\r\n")
    command_channel.readline()
    buffer = command_channel.readline()
    if not buffer:
      log.debug("Modem already powered off")
    else:
      log.debug("Powering off modem")
      GPIO.output(modem_power, GPIO.HIGH)
      while True:
        line = command_channel.readline().strip()
        if line == "NORMAL POWER DOWN":
          log.debug("Modem powered off")
          break
      GPIO.output(modem_power, GPIO.LOW)
      self.data_channel.close()

  def reset(self):
    log.debug("Resetting modem")
    GPIO.output(modem_reset, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(modem_reset, GPIO.LOW)
    log.debug("Modem reset done")

  def linestatus(self):
    self.linestatus_loop = True
    do_it = time.time()     # Set execute loop timing variable to "now"
    log.debug("Started linestatus check")
    while self.linestatus_loop:
      if time.time() > do_it:   # Execute these only if "now" is more than timing variable
        self.data_channel.isOpen()
        self.data_channel.write("AT+CREG?"+"\r\n")
        do_it = time.time() + 60  # Set timing variable 60 seconds from "now"
      time.sleep(1)
    log.debug("Stopped linestatus check")

class Pin:
  # Init (activate pin)
  def __init__(self):
    # Use RPi BOARD pin numbering convention
    GPIO.setmode(GPIO.BOARD)

    # Set up GPIO input channels
    # Lock opening button
    GPIO.setup(button_open_lock, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    log.debug("initialized lock opening button input, using pull up")
    # Keep lock unlocked switch
    GPIO.setup(switch_keep_lock_open, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    log.debug("initialized keep lock open switch input, using pull up")

    # Event detection for button/switch
    GPIO.add_event_detect(button_open_lock, GPIO.BOTH, callback=self.handle_lock, bouncetime=50)
    GPIO.add_event_detect(switch_keep_lock_open, GPIO.BOTH, callback=self.handle_lock, bouncetime=50)

    # Set up GPIO output channels
    # Lock
    GPIO.setup(lock, GPIO.OUT, initial=GPIO.HIGH)
    log.debug("initialized lock, pin to high")
    # Lock open indicator light
    GPIO.setup(locklight, GPIO.OUT, initial=GPIO.HIGH)
    log.debug("initialized lock open light, pin to high")
    # Modem power button
    GPIO.setup(modem_power, GPIO.OUT, initial=GPIO.LOW)
    log.debug("initialized modem_power, pin to low")
    # Modem reset button
    GPIO.setup(modem_reset, GPIO.OUT, initial=GPIO.LOW)
    log.debug("initialized modem_reset, pin to low")

  def open_lock(self):
    GPIO.output(lock, GPIO.LOW)
    log.debug("Opened lock")
    self.lock_open_light_on()

  def close_lock(self):
    GPIO.output(lock, GPIO.HIGH)
    log.debug("Closed lock")
    self.lock_open_light_off()

  def lock_open_light_on(self):
    GPIO.output(locklight, GPIO.LOW)
    log.debug("Lock open light on")

  def lock_open_light_off(self):
    GPIO.output(locklight, GPIO.HIGH)
    log.debug("Lock open light off")

  def handle_lock(self, channel):
    log.debug("Handle lock: got channel/GPIO: " + str(channel))

    if channel == switch_keep_lock_open:
      if not GPIO.input(switch_keep_lock_open):
        log.info("Keep lock open switch turned on")
        self.open_lock()
      if GPIO.input(switch_keep_lock_open):
        log.info("Keep lock open switch turned off")
        self.close_lock()

    if channel == button_open_lock:
      if not GPIO.input(button_open_lock):
        if not GPIO.input(switch_keep_lock_open):
          log.debug("Lock opening button pressed, keep lock open switch already on, pass")
        if GPIO.input(switch_keep_lock_open):
          log.info("Lock opening button pressed")
          self.send_pulse_lock()
      if GPIO.input(button_open_lock):
        log.debug("Lock opening button released")

    if channel == "modem":
      if not GPIO.input(switch_keep_lock_open):
        log.debug("Got modem call, keep lock open switch already on, pass")
      if GPIO.input(switch_keep_lock_open):
        log.info("Got modem call")
        self.send_pulse_lock()

  def send_pulse_lock(self):
    self.open_lock()
    # Keep pulse high for X second
    time.sleep(10)
    self.close_lock()
    log.debug("Lock opening pulse done")

class GateKeeper:
  linestatus = False
  load_whitelist_loop = False

  def __init__(self, config):
    self.whitelist = {}
#    self.load_whitelist_loop = True # Enable refreshing whitelist perioidically
    self.config = config
    self.pin = Pin()                # GPIO pins
    self.read_whitelist()           # Read whitelist on startup
    self.load_whitelist_interval = threading.Thread(target=self.load_whitelist_interval, args=())
    self.load_whitelist_interval.start() # Update whitelist perioidically
    self.modem = Modem()
    self.modem.power_on()
    self.modem.enable_caller_id()
    self.linestatus = threading.Thread(target=self.modem.linestatus, args=())
    self.linestatus.start()         # Check we are still registered on cellular network

  def url_log(self, name, number):
    try:
      data = {'key': config['api_key'], 'phone': number, 'message': name}
      r = requests.post(config['api_url'], data)
    except:
      log.debug('failed url for remote log')

  def matrix_message(self, name, number):
    try:
      url = 'https://' + config['MatrixHost'] + '/_matrix/client/r0/rooms/' + config['MatrixRoom'] + '/send/m.room.message'
      token = config['MatrixToken']
      msgtype = 'm.notice'
      message = 'Opened door for: ' + name
      r = requests.post(url, headers={'Authorization': 'Bearer ' + token}, json={'msgtype': msgtype, 'body': message})
      log.debug('success: Matrix message send')
    except Exception as e:
      log.debug('failed Matrix message operation, error:\n' + str(e))

  def mqtt_log(self, name, number):
    try:
      publish.single("door/name", name, hostname=config['MQTThost'])
      log.debug('success: MQTT remote log')
    except:
      log.debug('failed MQTT remote log operation')

  def dingdong(self):
    try:
      url = config['doorbell_url']
      r = requests.get(url)
      log.debug('success: url for doorbell')
    except:
      log.debug('failed url for doorbell')

  def load_whitelist_interval(self):
    log.debug('Started whitelist interval refreshing loop')
    do_it = time.time()
    while self.load_whitelist_loop: # Loop until told otherwise
      if time.time() > do_it:
        log.debug('Running whitelist interval refresh')
        try:
          self.load_whitelist()
        except Exception as e:
          log.error("Failed to load whitelist from " + config['whitelist_ssh_server'] + ", error:\n" + str(e) + "\nNot updating whitelist")
        else:
          self.read_whitelist()
        finally:
          do_it = time.time() + 60 * 60 # Run again after an hour (seconds * minutes)
      time.sleep(1) # Let loop sleep for 1 second until next iteration
    log.debug('Stopped whitelist interval refreshing loop')

  def read_whitelist(self):
    try:
      whitelistFileName = os.path.join(sys.path[0], 'whitelist.json.local')
      if not os.path.isfile(whitelistFileName):
        log.info(whitelistFileName + " doesn't exits (first time use?), trying to load one from " + config['whitelist_ssh_server'])
        self.load_whitelist()
      with open(whitelistFileName) as data_file:
        jsonList = json.load(data_file)
        self.whitelist.clear()
        log.debug("Cleared old phonenumber whitelist from RAM")

        for key, value in jsonList.items():
          if "PhoneNumber" in value:
            for phoneNumber in value["PhoneNumber"]:
              if phoneNumber[:4] == "+358":       # If phonenumber is finnish
                phoneNumber = "0"+phoneNumber[4:] # Replace '+358' with an '0'
              else:                               # Else number is international
                phoneNumber = phoneNumber[1:]     # Only remove the '+'
              self.whitelist[phoneNumber] = value["nick"]

        log.debug("Whitelist\n" + pformat(self.whitelist))

    except Exception as e:
      log.error("Failed to read whitelist from " + whitelistFileName + ", error:\n" + str(e) + "\nExiting Gatekeeper")
      self.exit_gatekeeper(1) # Tell gatekeeper to exit with error

  def load_whitelist(self):
    whitelistFileName = os.path.join(sys.path[0], 'whitelist.json')
    log.debug("Loading SSH-key from " + os.path.expanduser(config['whitelist_ssh_keyfile']))
    key = paramiko.Ed25519Key.from_private_key_file(os.path.expanduser(config['whitelist_ssh_keyfile']), password=config['whitelist_ssh_password'].encode("ascii"))
    transport = paramiko.Transport((config['whitelist_ssh_server'], config['whitelist_ssh_port']))
    try:
      # Set allowed SSH/SFTP parameters, we (try to) only allow secure ones, tuple format
      transport.get_security_options().ciphers = ('aes256-ctr', 'aes192-ctr', 'aes128-ctr')
      transport.get_security_options().kex = ('diffie-hellman-group-exchange-sha256',)
      transport.get_security_options().digests = ('hmac-sha2-512', 'hmac-sha2-256')
      transport.get_security_options().key_types = ('ssh-ed25519', 'ssh-rsa')

      log.info("Retrieving whitelist from " + config['whitelist_ssh_server'])
      transport.connect(username=config['whitelist_ssh_username'], pkey=key)
      sftp = paramiko.SFTPClient.from_transport(transport)
      sftp.get(config['whitelist_ssh_getfile'], whitelistFileName)
      log.debug("Whitelist retrieved")
      transport.close()
      log.debug("SFTP-connection closed")
      copyfile(whitelistFileName, whitelistFileName+".local")
      log.debug("Copied " + whitelistFileName + " into " + whitelistFileName + ".local")
    except Exception as e:
      log.error("Failed to load whitelist from " + config['whitelist_ssh_server']  + ", error:\n" + str(e))

  def wait_for_call(self):
    self.modem.data_channel.isOpen()
    call_id_pattern = re.compile('^\+CLIP: *"(\d*?)"')
    creg_pattern = re.compile('\+CREG: *\d,[^125]')
    while True:
      buffer = self.modem.data_channel.readline()
      call_id_match = call_id_pattern.match(buffer)
##
#      log.debug("Data from data channel: " +buffer.strip())
##

      if call_id_match:
        number = call_id_match.group(1)
        self.handle_call(number)

      if creg_pattern.match(buffer):
        log.debug("Not connected with line \n"+buffer)
        self.modem.reset()


  def handle_call(self,number):
    log.debug("Incoming call from: " + str(number))
    if number in self.whitelist:
      # Setup threads
      hangup = threading.Thread(target=self.modem.hangup, args=())
      handle_lock = threading.Thread(target=self.pin.handle_lock, args=("modem",))
      url_log = threading.Thread(target=self.url_log, args=(self.whitelist[number],number))
      matrix_message = threading.Thread(target=self.matrix_message, args=(self.whitelist[number],number))
      mqtt_log = threading.Thread(target=self.mqtt_log, args=(self.whitelist[number],number))
      # Execute letting people in -tasks
      hangup.start()
      handle_lock.start()
      url_log.start()
      matrix_message.start()
      mqtt_log.start()
      log.info("Opened the gate for " + self.whitelist[number] + " (" + number + ").")
      # Wait tasks to finish
      hangup.join()
      handle_lock.join()
      url_log.join()
      matrix_message.join()
      mqtt_log.join()
    else:
      if number == "":
        number = "Hidden"
      log.info("Did not open the gate for "  + number + ", number is not kown.")
      # Setup threads
      dingdong = threading.Thread(target=self.dingdong, args=())
      url_log = threading.Thread(target=self.url_log, args=("DENIED",number))
      matrix_message = threading.Thread(target=self.matrix_message, args=("DENIED",number))
      mqtt_log = threading.Thread(target=self.mqtt_log, args=("DENIED",number))
      # Ring doorbell and log denied number
      dingdong.start()
      url_log.start()
      matrix_message.start()
      mqtt_log.start()
      # Wait for caller hangup, so we log call only once instead on every ring, timeout 2 minutes
      data_channel = serial.Serial(port=data_port,baudrate=data_baudrate,parity=data_parity,stopbits=data_stopbits,bytesize=data_bytesize,xonxoff=data_xonxoff,rtscts=data_rtscts,dsrdtr=data_dsrdtr,timeout=1,writeTimeout=1)
      data_channel.isOpen()
      timestart = time.time()
      timeout = 60 * 2 # timeout set to 2 minutes
      while time.time() < timestart + timeout:
        line = data_channel.readline().strip()
        if line == "NO CARRIER":
          log.debug("Non whitelist caller hung up")
          break
      # Wait doorbell and log process to finish
      dingdong.join()
      url_log.join()
      matrix_message.join()
      mqtt_log.join()

  def start(self):
    signum = 0                          # Set error status as clean
    try:
      self.wait_for_call()
    except Exception as e:
      log.debug("error:\n" + str(e))
    except select.error as v:
      if v[0] == EINTR:
        log.debug("Caught EINTR")
      else:
        raise
    else:
      log.warning("Unexpected exception, shutting down!")
      signum = 1                        # Set error status as error

    finally:
      log.debug("Stopping GateKeeper")
      gatekeeper.stop_gatekeeping()
      log.debug("Shutdown tasks completed")
      log.info("GateKeeper Stopped")
      self.exit_gatekeeper(signum)     # Tell gatekeeper to exit with error status

  def stop_gatekeeping(self):
    # Setup threads
    closelock = threading.Thread(target=self.pin.close_lock, args=())
    modemoff = threading.Thread(target=self.modem.power_off, args=())
    # Do shutting down tasks
    closelock.start()                   # Close lock
    self.modem.linestatus_loop = False  # Tells modem linestatus check loop to stop
    self.linestatus.join()              # Wait linestatus thread to finish
    modemoff.start()                    # Tell modem to power off
    closelock.join()                    # Wait close lock to finish
    modemoff.join()                     # Wait modem off to finish
    self.load_whitelist_interval.join() # Wait whitelist loader loop to end

  def exit_gatekeeper(self, signum):
    GPIO.cleanup()                      # Undo all GPIO setups we have done
    sys.exit(signum)                    # Exit gatekeeper with signum as informal parameter (0 success, 1 error)

logging.info("Started GateKeeper")

gatekeeper = GateKeeper(config)

def shutdown_handler(signum, frame):
  sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

gatekeeper.start()
