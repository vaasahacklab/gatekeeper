#!/usr/bin/python
# -*- coding: utf-8 -*-

import serial            # Serial communication
import re                # Regular expressions
import logging           # Hmm what could this be for?
import os                # To call external stuff
import sys               # System calls
import signal            # Catch kill signal
import time              # For the sleep function
import select            # For select.error
from errno import EINTR  # Read interrupt
import traceback         # For stacktrace
import RPi.GPIO as GPIO  # For using Raspberry Pi GPIO
import threading         # For enabling multitasking
import requests          # HTTP library
import json              # JSON parser, for config file

# Setup logging
LOG_FILENAME = os.path.join(sys.path[0], 'gatekeeper.log')
FORMAT = "%(asctime)-12s: %(levelname)-8s - %(message)s"
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,format=FORMAT)
log = logging.getLogger("GateKeeper")

# Setup GPIO output pins
lock = 12
lights = 16
modem_power = 17
modem_reset = 18
out3 = 20
out4 = 21

# Setup GPIO input pins
latch = 5
lightstatus = 6
in3 = 13
in4 = 19
in5 = 26

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

# Load configuration file
log.debug("Loading config file...")

try:
  with open(os.path.join(sys.path[0], 'config.json'), 'r') as f:
    config = json.load(f)
except Exception, e:
  log.debug('Failed loading config file: ' + str(e))
  raise e

log.debug("Config file loaded.")

# Setup over, start defining classes

class Modem:
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
    while True:
      self.data_channel.isOpen()
      self.data_channel.write("AT+CREG?"+"\r\n")
      time.sleep(60)

class Pin:
  # Init (activate pin)
  def __init__(self):
    # Use BCM chip pin numbering convention
    GPIO.setmode(GPIO.BCM)

    # Set up GPIO input channels
    # Light on/off status
    GPIO.setup(lightstatus, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    # Door latch open/locked status
    GPIO.setup(latch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    GPIO.add_event_detect(latch, GPIO.BOTH, self.latch_moved)
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
  def __init__(self, config):
    self.config = config
    self.pin = Pin()
    self.read_whitelist()
    self.modem = Modem()
    self.modem.power_on()
    self.modem.enable_caller_id()
    linestatus = threading.Thread(target=self.modem.linestatus, args=())
    linestatus.daemon = True
    linestatus.start()
    
  def url_log(self, name, number):
    try:
      data = {'key': config['api_key'], 'phone': number, 'message': name}
      r = requests.post(config['api_url'], data)
    except:
      log.debug('failed url for remote log')

  def dingdong(self):
    try:
      r = requests.get('http://musicbox.lan:8080')
    except:
      log.debug('failed url for doorbell')

  def read_whitelist(self):
    self.whitelist = {}
    file = open('/home/ovi/gatekeeper/whitelist','r')
    entry_pattern = re.compile('([0-9][0-9]+?) (.*)')
    line = file.readline()
    while line:
      entry_match = entry_pattern.match(line)
      if entry_match:
        number = entry_match.group(1)
        name = entry_match.group(2)
        self.whitelist[number] = name
      line = file.readline()
    file.close()
    log.debug("Whitelist " + str(self.whitelist))

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
    log.debug(number)
    if number in self.whitelist:
      # Setup threads
      hangup = threading.Thread(target=self.modem.hangup, args=())
      lock_pulse = threading.Thread(target=self.pin.send_pulse_lock, args=())
      url_log = threading.Thread(target=self.url_log, args=(self.whitelist[number],number))
      # Execute letting people in -tasks
      hangup.start()
      lock_pulse.start()
      url_log.start()
      log.info("Opened the gate for " + self.whitelist[number] + " (" + number + ").")
      # Wait tasks to finish
      hangup.join()
      lock_pulse.join()
      url_log.join()
    else:
      if number == "":
        number = "Hidden"
      log.info("Did not open the gate for "  + number + ", number is not kown.")
      # Setup threads
      dingdong = threading.Thread(target=self.dingdong, args=())
      url_log = threading.Thread(target=self.url_log, args=("DENIED",number))
      # Ring doorbell and log denied number 
      dingdong.start()
      url_log.start()
      # Wait for caller hangup, so we log call only once instead on every ring, timeout 2 minutes
      data_channel = serial.Serial(port=data_port,baudrate=data_baudrate,parity=data_parity,stopbits=data_stopbits,bytesize=data_bytesize,xonxoff=data_xonxoff,rtscts=data_rtscts,dsrdtr=data_dsrdtr,timeout=1,writeTimeout=1)
      data_channel.isOpen()
      timestart = time.time()
      timeout = 60 * 2
      while time.time() < timestart + timeout:
        line = data_channel.readline().strip()
        if line == "NO CARRIER":
          log.debug("Non whitelist caller hung up")
          break
      # Wait doorbell and log precess to finish
      dingdong.join()
      url_log.join()
      
  def start(self):
    try: 
      self.wait_for_call()
    except select.error, v:
      if v[0] == EINTR:
        log.debug("Caught EINTR")
      else:
        raise
    else:
      log.warning("Unexpected exception, shutting down!")
    finally:
      log.debug("Stopping GateKeeper")
      gatekeeper.stop_gatekeeping()
      log.debug("Shutdown tasks completed")
      log.info("GateKeeper Stopped")
      
  def stop_gatekeeping(self):
    # Setup threads
    closelock = threading.Thread(target=self.pin.lockclose, args=())
    lightsoff = threading.Thread(target=self.pin.lightsoff, args=())
    modemoff = threading.Thread(target=self.modem.power_off, args=())
    # Do shutting down tasks
    closelock.start()
    lightsoff.start()
    modemoff.start()
    # Wait tasks to finish
    closelock.join()
    lightsoff.join()
    modemoff.join()
    # Undo all GPIO setups we have done
    GPIO.cleanup()


logging.info("Started GateKeeper")

gatekeeper = GateKeeper(config)

def shutdown_handler(signum, frame):
  sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

gatekeeper.start()
