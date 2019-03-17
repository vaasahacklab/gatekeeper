#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import serial
from time import sleep

__all__ = ["Modem"]

class Modem:
    def __init__(self):
        self.log = logging.getLogger(__name__.capitalize())
        self.modem_list = []
        self.available_modems = []
        self.thread_list = []

    def start(self, config):
        self.log.debug("start")
        # Read urllog settings from global config and store needed data in module-wide table
        for key, value in config.items():
            if key.upper() == "MODEM":
                for section in value:
                    self.modem_list.append(section)
        # Try loading module for each modem model in modem_list and store succeeded module names in available_modems table
        for device in self.modem_list:
            try:
                model = str(device['model'].lower())
                self.log.debug("Importing device file for: " + model)
                self.r = __import__(model)
                self.log.debug(self.r)
                self.log.debug("Adding " + model + " to available_modems")
                self.available_modems.append(device)
            except Exception as e:
                self.log.error("Failed to import device file for model: " + model + ", got error:\n " + str(e) + "\n Skipping import")
        #for device in self.available_modems:
        self.start_devices()
            
    def start_devices(self):
        for device in self.available_modems:
            t = threading.Thread(name="Modem-" + device['model'], target=self.power_on, args=(device['model'],))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()

    def power_on(self, model):
        self.log.debug("Powering on: " + model)
        # Figure out way to call variable value as function !!!
        nekku = self.r.rpisim800()
        nekku.start(config)

    def stop(self):
        for thread in self.thread_list:
            thread.join()
        self.log.debug("doned")

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os                   # To call external stuff
    import sys                  # System calls
    import json                 # For parsing config file

    # Setup logging as we are standalone
    import logging.config
    logging.config.fileConfig("logging.ini")
    log = logging.getLogger(__name__)

    # Load config from file as we are standalone
    log.debug("Loading config file...")
    try:
        with open(os.path.join(sys.path[0], "config.json"), "r") as f:
            config = json.load(f)
    except Exception as e:
        log.error("Failed loading config file: " + str(e))
        raise e
    log.debug("Config file loaded.")

    log.debug("Testing modem")
    Modem = Modem()
    Modem.start(config)
    Modem.stop()

