#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, logging.config
logging.config.fileConfig("logging.ini")

import os                   # To call external stuff
import sys                  # System calls
#import threading            # For enabling multitasking
import json                 # For parsing config file

from time import sleep
import urllog
import matrix
import mqtt

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
#        self.Modem = Modem.Modem()
        self.Urllog = urllog.Urllog(config)
        self.Matrix = matrix.Matrix(config)
        self.Mqtt = mqtt.Mqtt(config)

    def start_modules(self):
        pass
#        self.Modem.start(config)
#        self.Urllog.start(config)
#        self.Matrix.start(config)
#        self.Mqtt.start(config)

    def stop_modules(self):
#        self.Modem.stop()
        self.Urllog.stop()
        self.Matrix.stop()
        self.Mqtt.stop()

    def start(self):
        log.info("Starting Gatekeeper")
        self.start_modules()

        data1 = "Herra Pyyttoni"
        data2 = "+358000000000"
        data3 = "door/name"
        log.debug("Calling urllog with data1 as name: \"" + data1 + "\" and data2 as number: \"" + data2 + "\"")
        self.Urllog.send(message=data1, number=data2)
        log.debug("Calling matrix with data1 as name: \"" + data1 + "\" and data2 as number: \"" + data2 + "\"")
        self.Matrix.send(message=data1, number=data2)
        log.debug("Calling mqtt with data3 as mqtt topic: \"" + data2 + "\" and data1 as name/payload: \"" + data1 + "\"")
        self.Mqtt.send(topic=data3, message=data1)

        self.stop()

    def stop(self):
        log.debug("Stopping")
        self.stop_modules()
        log.info("Stopped")

gatekeeper = Gatekeeper(config)
gatekeeper.start()