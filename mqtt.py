#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import paho.mqtt.client as paho
from threading import Thread

__all__ = ["Mqtt"]

class Mqtt:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []

        # Read MQTT settings from global config and build thread list per instance
        for key, value in config.items():
            if key.upper() == "MQTT":
                for section in value:
                    self.server_list.append(section)
        if not self.server_list:
            self.log.info("No \"" + __name__ + "\" config parameters found, nothing to do.")

    def send(self, topic, nick):
        for server in self.server_list:
            t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['host'], topic, nick))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()

    def waitSendFinished(self):
        for thread in self.thread_list:
            thread.join()

    def _send(self, name, host, topic, nick):
        client = paho.Client(name)
        try:
            self.log.info(name + ": Publishing: \"" + topic + "\", \"" + nick + "\"")
            client.connect(host)
            r = client.publish(topic, nick)
            self.log.debug(name + ": Result: " + str(r))
            if r:
                client.disconnect()
        except Exception as e:
            self.log.error(name + ": Failed to connect to: " + host + " got error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json

    __name__ = "Mqtt"

    # Setup logging to stdout
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger(__name__)

    log.info("Running standalone, testing MQTT sender")

    # Load config from file
    log.debug("Loading config file")
    try:
        with open(os.path.join(sys.path[0], "config.json"), "r") as f:
            config = json.load(f)
        f.close()
    except ValueError as e:
        log.critical("config.json is malformed, got error:\n\t" + str(e))
        f.close()
    except Exception as e:
        log.critical("Failed loading config file, got error:\n\t" + str(e))

    Mqtt = Mqtt(config)

    Mqtt.send(topic="door/name", nick="Gatekeeper testmessage")
    Mqtt.waitSendFinished()
