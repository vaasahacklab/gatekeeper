#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os                   # To call external stuff
import sys                  # System calls
import threading            # For enabling multitasking
import json                 # JSON parser, for config file

# Load configuration file
print("Loading config file...")

try:
    with open(os.path.join(sys.path[0], 'config.json.example'), 'r') as f:
        config = json.load(f)
except Exception as e:
    print('Failed loading config file: ' + str(e))
    raise e

print("Config file loaded.")

class JsonParserTest:
    def __init__(self, config):
        print("Initialising JSON Parser Tester\n")

    def start(self):
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

jsonparsertest = JsonParserTest(config)
jsonparsertest.start()
