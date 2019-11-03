#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, logging.config
logging.config.fileConfig("logging.ini")

import os                   # To call external stuff
import sys                  # System calls
#import threading            # For enabling multitasking
import json                 # For parsing config file

from time import sleep
import mqtt
import urllog

log = logging.getLogger("Gatekeeper")

# Load configuration file
log.debug("Loading config file...")
try:
    with open(os.path.join(sys.path[0], "config.json"), "r") as f:
        config = json.load(f)
        log.debug("Config file loaded.")
except Exception as e:
    log.error("Failed loading config file: " + str(e))
    raise e

class Gatekeeper:
    def __init__(self, config):
        log.debug("Initialising Gatekeeper")
        self.Modem = Modem.Modem()
        self.Mqtt = mqtt.Mqtt()
        self.Urllog = urllog.Urllog()

    def start_modules(self):
        self.Modem.start(config)
        self.Mqtt.start(config)
        self.Urllog.start(config)

    def stop_modules(self):
        self.Modem.stop()
        self.Mqtt.stop()
        self.Urllog.stop()

    def start(self):
        log.info("Starting Gatekeeper")
        self.start_modules()

        data1 = "00000000"
        data2 = "Gatekeeper"
        data3 = "door/name"
        log.debug("Calling urllog with data1 as number: \"" + data1 + "\" and data2 as name: \"" + data2 + "\"")
        self.Urllog.send(data1, data2)
        log.debug("Calling mqtt with data3 as mqtt topic: \"" + data2 + "\" and data2 as name/payload: \"" + data2 + "\"")
        self.Mqtt.send(data3, data2)


        self.stop()

    def stop(self):
        log.debug("Stopping")
        self.stop_modules()
        log.info("Stopped")

gatekeeper = Gatekeeper(config)
gatekeeper.start()

"""     
        data1 = "00000000"
        data2 = "Gatekeeper"
        data3 = "door/name"
        log.debug("Calling urllog with data1 as number: \"" + data1 + "\" and data2 as name: \"" + data2 + "\"")
        self.urllog.send(data1, data2)
        log.debug("Calling mqtt with data3 as mqtt topic: \"" + data2 + "\" and data2 as name/payload: \"" + data2 + "\"")
        self.mqtt.send(data3, data2)

"""

