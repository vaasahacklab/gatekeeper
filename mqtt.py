#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import json
from time import sleep
import paho.mqtt.client as paho

__all__ = ["mqtt"]

class mqtt:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.server_list = []

    def start(self, config):
        # Read MQTT-server settings from global config and store needed data in module-wide table
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
            self.log.debug(name + ": Publishing: \"" + topic + "\", \"" + payload + "\" to host: " + host)
            client.connect(host)
            client.publish(topic, payload)
            client.disconnect()
        except Exception as e:
            self.log.error(name + ": Failed to connect to: " + host + " got error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os                   # To call external stuff
    import sys                  # System calls

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

    log.debug("Testing mqtt")
    mqtt = mqtt()
    mqtt.start(config)
    mqtt.send("door/name", "MQTT testmessage")