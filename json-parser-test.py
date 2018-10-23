#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, logging.config
logging.config.fileConfig("logging.ini")

import os                   # To call external stuff
import sys                  # System calls
#import threading            # For enabling multitasking
import json                 # JSON parser, for config file
from time import sleep
import mqtt
import urllog

log = logging.getLogger("JsonParserTest")

# Load configuration file
log.debug("Loading config file...")
try:
    with open(os.path.join(sys.path[0], "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    log.error("Failed loading config file: " + str(e))
    raise e
log.debug("Config file loaded.")

class JsonParserTest:
    def __init__(self, config):
        log.info("Initialising JSON Parser Tester")
        self.mqtt = mqtt.mqtt()
        self.urllog = urllog.urllog()

    def start(self):
        log.info("Starting JsonParserTest")
        data1 = "00000000"
        data2 = "JsonParserTest"
        data3 = "door/name"
        log.debug("Calling urllog with data1 as number: \"" + data1 + "\" and data2 as name: \"" + data2 + "\"")
        self.urllog.send(data1, data2)
        log.debug("Calling mqtt with data3 as mqtt topic: \"" + data2 + "\" and data2 as name/payload: \"" + data2 + "\"")
        self.mqtt.send(data3, data2)
        self.stop()

    def stop(self):
        log.debug("doned")

jsonparsertest = JsonParserTest(config)
jsonparsertest.start()

"""
        print("print(\"config\"):\n")
        print(" " + str(config) + "\n\n")

        print("for key, value in config.items, print key, value:\n")
        for key, value in config.items():
            print(" " + str(key) + str(value) + "\n")

        print("for mqttserver in config['mqtt']:\n")
        for mqttserver in config['mqtt']:
            print("print(mqttserver):\n")
            print("", mqttserver, "\n")
            print("print(mqttserver['name'] + \", \" + mqttserver['host'])" + "\n")
            print(" " + mqttserver['name'] + ", " + mqttserver['host'] + "\n")

        print("names\n")
        for key, value in config.items():
            for k in value:
                print("", type(k))
                if type(k) == dict:
                    print(" is dict: ", k)
                    print(" name:", k['name'], "\n")
                if type(k) == str:
                    print(" is str: ", k, "\n")

        print("mqtt specifically\n")
        for key, value in config.items():
            if key == "mqtt":
                for k in value:
                    print(" key name:", key)
                    print(" name:", k['name'])
                    print(" host:", k['host'], "\n")

"""