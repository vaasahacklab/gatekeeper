for key, value in config.items():
     if "doorbell" in key:
         for instance in value:
             print("nimi on:", instance["name"], "uusi urli on:", 
                instance["url"])



#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging              # Logging facilities
logging.config.fileConfig("logging.ini")

import re                   # Regular expressions
import os                   # To call external stuff
import sys                  # System calls
import signal               # Catch kill signal
import time                 # For the sleep function
import select               # For select.error
from errno import EINTR     # Read interrupt
import traceback            # For stacktrace
import RPi.GPIO as GPIO     # For using Raspberry Pi GPIO
import threading            # For enabling multitasking
import requests             # HTTP library
import MFRC522              # RFID reader
import json                 # JSON parser, for config file
from shutil import copyfile # File copying
import paramiko             # SSH access library
import paho.mqtt.publish as publish # MQTT messages
from pprint import pformat  # Pretty Print formatting

# Setup logging
log = logging.getLogger("Gatekeeper")
audit_log = logging.getLogger("Audit")

# Load configuration file
log.debug("Loading config file...")
try:
    with open(os.path.join(sys.path[0], 'config.json'), 'r') as f:
    config = json.load(f)
except Exception as e:
    log.debug('Failed loading config file: ' + str(e))
    raise e
log.debug("Config file loaded.")

class Pin:
  # Init (activate pin)
  def __init__(self):
    # Use RPi BOARD pin numbering convention
    GPIO.setmode(GPIO.BOARD)

    # Set up GPIO input channels
    # Light on/off status
    GPIO.setup(lightstatus, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    # Door latch open/locked status
    GPIO.setup(latch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.add_event_detect(latch, GPIO.BOTH, callback=self.latch_moved, bouncetime=500)
    # Currently unused inputs on input-relay board. initialize them anyway
    GPIO.setup(in3, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.setup(in4, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.setup(in5, GPIO.IN, pull_up_down = GPIO.PUD_UP)

    # Set up GPIO output channels
    # Lock
    GPIO.setup(lock, GPIO.OUT, initial=GPIO.HIGH)
    log.debug("initialized lock, pin to high")
    # Lights
    GPIO.setup(lights, GPIO.OUT, initial=GPIO.HIGH)
    log.debug("initialized lights, pin to high")
    # Modem power button
    GPIO.setup(modem_power, GPIO.OUT, initial=GPIO.LOW)
    log.debug("initialized modem_power, pin to low")
    # Modem reset button
    GPIO.setup(modem_reset, GPIO.OUT, initial=GPIO.LOW)
    log.debug("initialized modem_reset, pin to low")
    # Currently unused outputs on output-relay board, initialize them anyway
    GPIO.setup(out3, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(out4, GPIO.OUT, initial=GPIO.HIGH)

  def lockopen(self):
    GPIO.output(lock, GPIO.LOW)
    log.debug("Opened lock")

  def lockclose(self):
    GPIO.output(lock, GPIO.HIGH)
    log.debug("Closed lock")

  def lightson(self):
    GPIO.output(lights, GPIO.LOW)
    log.debug("Lights to on")

  def lightsoff(self):
    GPIO.output(lights, GPIO.HIGH)
    log.debug("Lights to off")

  def send_pulse_lock(self):
    self.lockopen()
    # Keep pulse high for 5.5 second
    time.sleep(5.5)
    self.lockclose()
    log.debug("Lock opening pulse done")

  def latch_moved(channel, event):
    if GPIO.input(latch):     # If latch GPIO == 1. When latch is opened, sensor drops to 0, relay opens, GPIO pull-up makes GPIO 1
      log.debug('Door latch opened')
    else:                     # If latch GPIO != 1. When latch is closed, sensor goes to 1, relay closes, GPIO goes 0 trough raspberry GND-pin
      log.debug('Door latch closed')

class GateKeeper:
  # Introduce program-loop parameters, initially disabled
  wait_for_tag = False
  read_rfid_loop = False
  linestatus = False
  load_whitelist_loop = False

  def __init__(self, config):
    self.rfidwhitelist = {}         # Introduce whitelist parameters
    self.whitelist = {}
    self.read_rfid_loop = True      # Enable reading RFID
    self.load_whitelist_loop = True # Enable refreshing whitelist perioidically
    self.config = config
    self.pin = Pin()                # GPIO pins
    self.read_whitelist()           # Read whitelist on startup
    self.load_whitelist_interval = threading.Thread(target=self.load_whitelist_interval, args=())
    self.load_whitelist_interval.start() # Update whitelist perioidically
    self.wait_for_tag = threading.Thread(target=self.wait_for_tag, args=())
    self.wait_for_tag.start()       # Start RFID-tag reader routine
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
        self.rfidwhitelist.clear()
        log.debug("Cleared old RFID-number whitelist from RAM")

        for key, value in jsonList.items():
          if "PhoneNumber" in value:
            for phoneNumber in value["PhoneNumber"]:
              if phoneNumber[:4] == "+358":       # If phonenumber is finnish
                phoneNumber = "0"+phoneNumber[4:] # Replace '+358' with an '0'
              else:                               # Else number is international
                phoneNumber = phoneNumber[1:]     # Only remove the '+'
              self.whitelist[phoneNumber] = value["nick"]

          if "RFID" in value:
            for rfidTag in value["RFID"]:
              self.rfidwhitelist[rfidTag] = value["nick"]

        log.debug("Whitelist\n" + pformat(self.whitelist))
        log.debug("RFID Whitelist\n " + pformat(self.rfidwhitelist))

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

  def wait_for_tag(self):
    log.debug("Started RFID-tag reader")
    MIFAREReader = MFRC522.MFRC522()
    # Set RFID-antenna gain to maximum, 48dB, register value of 0x07
    MIFAREReader.ClearBitMask(MIFAREReader.RFCfgReg, (0x07<<4))
    MIFAREReader.SetBitMask(MIFAREReader.RFCfgReg, (0x07<<4))
    while self.read_rfid_loop:
      time.sleep(1)
      # Scan for cards
      (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
      # If a card is found
      if status == MIFAREReader.MI_OK:
        log.debug("RFID Card detected")
        # Get the UID of the card
        (status,uid) = MIFAREReader.MFRC522_Anticoll()
        # If we have the UID, continue
        if status == MIFAREReader.MI_OK:
          tag_id = str(uid[0])+str(uid[1])+str(uid[2])+str(uid[3])
          self.handle_rfid(tag_id)
    log.debug("Stopped RFID-tag reader")

  def handle_rfid(self,tag_id):
    if tag_id in self.rfidwhitelist:
      # Setup threads
      lock_pulse = threading.Thread(target=self.pin.send_pulse_lock, args=())
      url_log = threading.Thread(target=self.url_log, args=(self.rfidwhitelist[tag_id],tag_id))
      mqtt_log = threading.Thread(target=self.mqtt_log, args=(self.rfidwhitelist[tag_id],tag_id))
      # Execute letting people in -tasks
      lock_pulse.start()
      url_log.start()
      mqtt_log.start()
      log.info("Opened the gate for RFID tag " + self.rfidwhitelist[tag_id] + " (" + tag_id + ").")
      # Wait tasks to finish
      lock_pulse.join()
      url_log.join()
      mqtt_log.join()
    else:
      log.info("Did not open the gate for RFID tag "  + tag_id + ", tag UID is not kown.")
      # Setup threads
      dingdong = threading.Thread(target=self.dingdong, args=())
      url_log = threading.Thread(target=self.url_log, args=("DENIED",tag_id))
      mqtt_log = threading.Thread(target=self.mqtt_log, args=("DENIED",tag_id))
      # Ring doorbell and log denied RFID tag
      dingdong.start()
      url_log.start()
      mqtt_log.start()
      # Wait tasks to finish
      dingdong.join()
      url_log.join()
      mqtt_log.join()

  def handle_call(self,number):
    log.debug("Incoming call from: " + str(number))
    if number in self.whitelist:
      # Setup threads
      hangup = threading.Thread(target=self.modem.hangup, args=())
      lock_pulse = threading.Thread(target=self.pin.send_pulse_lock, args=())
      url_log = threading.Thread(target=self.url_log, args=(self.whitelist[number],number))
      mqtt_log = threading.Thread(target=self.mqtt_log, args=(self.whitelist[number],number))
      # Execute letting people in -tasks
      hangup.start()
      lock_pulse.start()
      url_log.start()
      mqtt_log.start()
      log.info("Opened the gate for " + self.whitelist[number] + " (" + number + ").")
      # Wait tasks to finish
      hangup.join()
      lock_pulse.join()
      url_log.join()
      mqtt_log.join()
    else:
      if number == "":
        number = "Hidden"
      log.info("Did not open the gate for "  + number + ", number is not kown.")
      # Setup threads
      dingdong = threading.Thread(target=self.dingdong, args=())
      url_log = threading.Thread(target=self.url_log, args=("DENIED",number))
      mqtt_log = threading.Thread(target=self.mqtt_log, args=("DENIED",number))
      # Ring doorbell and log denied number
      dingdong.start()
      url_log.start()
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
      # Wait doorbell and log precess to finish
      dingdong.join()
      url_log.join()
      mqtt_log.join()

  def start(self):
    signum = 0                          # Set error status as clean
    try:
      self.wait_for_call()
      self.wait_for_tag()
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
    closelock = threading.Thread(target=self.pin.lockclose, args=())
    lightsoff = threading.Thread(target=self.pin.lightsoff, args=())
    modemoff = threading.Thread(target=self.modem.power_off, args=())
    # Do shutting down tasks
    self.read_rfid_loop = False         # Tells RFID-reading loop to stop
    self.load_whitelist_loop = False    # Tells whitelist loader loop to stop
    closelock.start()                   # Close lock
    lightsoff.start()                   # Turn off lights
    self.modem.linestatus_loop = False  # Tells modem linestatus check loop to stop
    self.linestatus.join()              # Wait linestatus thread to finish
    modemoff.start()                    # Tell modem to power off
    closelock.join()                    # Wait close lock to finish
    lightsoff.join()                    # Wait lights off to finish
    modemoff.join()                     # Wait modem off to finish
    self.wait_for_tag.join()            # Wait RFID tag reading loop to end
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