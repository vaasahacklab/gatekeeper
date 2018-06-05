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
import traceback            # For stacktrace
import RPi.GPIO as GPIO     # For using Raspberry Pi GPIO
import threading            # For enabling multitasking
import requests             # HTTP library
import MFRC522              # RFID reader
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

# GPIO in
modem_power = 11
modem_reset = 12

motor_left_switch = 36
motor_right_switch = 37
lock_left_switch = 38
lock_right_switch = 40

button_open = 33

# GPIO out
lock_turn_left_pin = 29
lock_turn_right_pin = 31

# Motor spin speed PWM
motor_pwm_pin = 32

# Motor PWM parameters
motor_pwm_dutycycle = 70
motor_pwm_hz = 6000

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

    GPIO.setup(modem_power, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(modem_reset, GPIO.OUT, initial=GPIO.LOW)

    GPIO.setup(motor_left_switch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.setup(motor_right_switch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.setup(lock_left_switch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.setup(lock_right_switch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.setup(lock_turn_left_pin, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(lock_turn_right_pin, GPIO.OUT, initial=GPIO.LOW)

    GPIO.setup(motor_pwm_pin, GPIO.OUT, initial=GPIO.LOW)
    self.enable_motor_pwm = GPIO.PWM(motor_pwm_pin, motor_pwm_hz)

    GPIO.setup(button_open, GPIO.IN, pull_up_down = GPIO.PUD_UP)

  def read_button_open(self):
    log.debug("Door opening button enabled")
    self.enable_button = True
    while self.enable_button:
      channel = GPIO.wait_for_edge(button_open, GPIO.FALLING, timeout=1000)
      if channel is None:
        pass
      else:
        log.info("Door opening button pressed")
        self.send_pulse_lock()
    log.debug("Door opening button disabled")

  def send_pulse_lock(self):
    self.unlock_door()
    time.sleep(10)
    self.lock_door()

  def unlock_door(self):
#    print("\nBefore unlock function:"
#      + "\nMotor left: " + str(GPIO.input(motor_left_switch))
#      + "\nMotor right: " + str(GPIO.input(motor_right_switch))
#      + "\n")
    if GPIO.input(motor_left_switch) and GPIO.input(motor_right_switch) == 0:
      log.debug("Lock motor already at leftmost position")
    elif GPIO.input(motor_left_switch) and GPIO.input(motor_right_switch):
      log.debug("Doorlock is locked, can open")
      log.info("Unlocking door")
      motor_left_switch_pin_count = 0
      GPIO.add_event_detect(motor_left_switch, GPIO.FALLING, bouncetime=50)
      GPIO.add_event_detect(motor_right_switch, GPIO.RISING, bouncetime=50)

      self.enable_motor_pwm.start(motor_pwm_dutycycle)
      GPIO.output(lock_turn_right_pin, GPIO.LOW)
      GPIO.output(lock_turn_left_pin, GPIO.HIGH)

      while not (motor_left_switch_pin_count == 3 and GPIO.event_detected(motor_right_switch)):
        if GPIO.event_detected(motor_left_switch):
          motor_left_switch_pin_count += 1
          #print("pin count: " + str(motor_left_switch_pin_count))
      log.debug("Unlock success")
      GPIO.remove_event_detect(motor_left_switch)
      GPIO.remove_event_detect(motor_right_switch)
      self.stop_motor()
    else:
      log.debug("Else reached, dunno lol")
#    print("after if")
#    print("\nAfter unlock function:"
#      + "\nMotor left: " + str(GPIO.input(motor_left_switch))
#      + "\nMotor right: " + str(GPIO.input(motor_right_switch))
#      + "\n")

  def lock_door(self):
#    print("\nBefore lock function:"
#      + "\nMotor left: " + str(GPIO.input(motor_left_switch))
#      + "\nMotor right: " + str(GPIO.input(motor_right_switch))
#      + "\n")
#    print("Locking door function")
    if GPIO.input(motor_left_switch) and GPIO.input(motor_right_switch):
      log.debug("Lock motor already at rightmost position")
    elif GPIO.input(motor_left_switch) == 0 or GPIO.input(motor_right_switch) == 0:
      log.info("Locking door")
      self.enable_motor_pwm.start(motor_pwm_dutycycle)
      GPIO.output(lock_turn_right_pin, GPIO.HIGH)
      GPIO.output(lock_turn_left_pin, GPIO.LOW)

      while not (GPIO.input(motor_left_switch) and GPIO.input(motor_right_switch)):
        pass
      self.stop_motor()
      log.debug("Lock success")
      time.sleep(0.5)

      log.debug("Adjusting lock motor-ring postition to be exactly locked")
      self.enable_motor_pwm.start(13)
      GPIO.output(lock_turn_right_pin, GPIO.LOW)
      GPIO.output(lock_turn_left_pin, GPIO.HIGH)

      while not (GPIO.input(motor_left_switch) and GPIO.input(motor_right_switch)):
        pass
      self.stop_motor()
      log.debug("Adjusting lock motor-ring postition success")

    else:
      log.debug("Else reached, dunno lol")
#    print("after if")
#    print("\nAfter lock function:"
#      + "\nMotor left: " + str(GPIO.input(motor_left_switch))
#      + "\nMotor right: " + str(GPIO.input(motor_right_switch))
#      + "\n")

  def stop_motor(self):
    log.debug("Stopping lock motor")
    GPIO.output(lock_turn_right_pin, GPIO.LOW)
    GPIO.output(lock_turn_left_pin, GPIO.LOW)
    self.enable_motor_pwm.stop()

class GateKeeper:
  # Introduce program-loop parameters, initially disabled
  wait_for_tag = False
  read_rfid_loop = False
  linestatus = False
  load_whitelist_loop = False
  enable_button = False

  def __init__(self, config):
    self.rfidwhitelist = {}         # Introduce whitelist parameters
    self.whitelist = {}
    self.read_rfid_loop = True      # Enable reading RFID
    self.load_whitelist_loop = True # Enable refreshing whitelist perioidically
    self.config = config
    self.pin = Pin()                # GPIO pins
    self.button = threading.Thread(target=self.pin.read_button_open, args=())
    self.button.start()             # Read door opening button
    self.read_whitelist()           # Read whitelist on startup
    self.pin.lock_door()            # Lock door, this ensures correct starting state if locking state is unkown
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
    closelock = threading.Thread(target=self.pin.lock_door, args=())
    modemoff = threading.Thread(target=self.modem.power_off, args=())
    # Do shutting down tasks
    self.read_rfid_loop = False         # Tells RFID-reading loop to stop
    self.load_whitelist_loop = False    # Tells whitelist loader loop to stop
    self.pin.enable_button = False      # Tells button reader to stop
    closelock.start()                   # Close lock
    self.modem.linestatus_loop = False  # Tells modem linestatus check loop to stop
    self.linestatus.join()              # Wait linestatus thread to finish
    modemoff.start()                    # Tell modem to power off
    closelock.join()                    # Wait close lock to finish
    modemoff.join()                     # Wait modem off to finish
    self.wait_for_tag.join()            # Wait RFID tag reading loop to end
    self.load_whitelist_interval.join() # Wait whitelist loader loop to end
    self.button.join()                  # Wait button reader loop to end

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
