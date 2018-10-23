#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os                   # To call external stuff
import sys                  # System calls
import threading
import json
from time import sleep
import paho.mqtt.client as paho

__all__ = ["mqtt"]

log = logging.getLogger(__name__)

log.debug("Loading config file...")
try:
    with open(os.path.join(sys.path[0], "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    log.error("Failed loading config file: " + str(e))
    raise e
log.debug("Config file loaded.")

class mqtt:
    def __init__(self):
        self.server_list = []

        # Read MQTT-server settings from global config json and store in module-wide table
        for key, value in config.items():
            if key == "mqtt":
                for section in value:
                    self.server_list.append(section)

    def send(self, topic, payload):
        thread_list = []
        for server in self.server_list:
            t = threading.Thread(name="mqtt-" + server['name'], target=self.send_message, args=(server['name'], server['host'], topic, payload))
            thread_list.append(t)
        
        for thread in thread_list:
            thread.start()
        
    def send_message(self, name, host, topic, payload):
        client = paho.Client(name)
        try:
            log.debug(name + ": Publishing: \"" + topic + "\", \"" + payload + "\" to host: " + host)
            client.connect(host)
            client.publish(topic, payload)
            client.disconnect()
        except Exception as e:
            log.error(name + ": Failed to connect to: " + host + " got error:\n  " + str(e))

# Test routine if module is run as main program
if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig("logging.ini", disable_existing_loggers = False)

    log.debug("Testing mqtt")
    mqtt = mqtt()
    mqtt.send("door/name", "MQTT testmessage")