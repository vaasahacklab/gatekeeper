#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, logging.config
logging.config.fileConfig("logging.ini")

import os                   # To call external stuff
import sys                  # System calls
import signal               # Catch kill signal
import select               # For select.error
from errno import EINTR     # Read interrupt
import traceback            # For stacktrace
import RPi.GPIO as GPIO     # For using Raspberry Pi GPIO
import threading            # For enabling multitasking
import requests             # HTTP library
import json                 # JSON parser, for config file

import modem                # Modem inputmodule

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

class GateKeeper:
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