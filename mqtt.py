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
            if key.upper() == __name__.upper():
                for section in value:
                    self.server_list.append(section)
        if not self.server_list:
            self.log.info("No \"" + __name__ + "\" config parameters found, nothing to do.")

    def start(self):
        if self.server_list:
            self.log.debug("Starting")
            self.log.debug("Started")

    def send(self, result, querytype, token, email=None, firstName=None, lastName=None, nick=None, phone=None):
        if self.server_list:
            for server in self.server_list:
                self.log.info(server['name'] + ": Sending data")
                if server['staff']:
                    if 200 <= result <= 299:
                        data = {'querytype': querytype, 'token': token, 'email': email, 'firstName': firstName, 'lastName': lastName, 'nick': nick, 'phone': phone}
                    elif result == 480:
                        data = {'querytype': querytype, 'token': token, 'nick': "DENIED"}
                    elif result == 481:
                        data = {'querytype': querytype, 'token': token, 'nick': "DENIED"}
                    else:
                        data = None
                else:
                    if 200 <= result <= 299:
                        data = {'nick': nick}
                    elif result == 480:
                        data = {'nick': "DENIED"}
                    elif result == 481:
                        data = {'nick': "DENIED"}
                    else:
                        data = None
            if data:
                for key in data:
                    topic = "Gatekeeper/door/" + str(key)
                    message = str(data[key])
                    t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['host'], topic, message))
                    self.thread_list.append(t)
                for thread in self.thread_list:
                    thread.start()

    def waitSendFinished(self):
        for thread in self.thread_list:
            thread.join()

    def stop(self):
        if self.server_list:
            self.log.debug("Stopping")
            self.waitSendFinished()
            self.log.debug("Stopping")

    def _send(self, name, host, topic, message):
        client = paho.Client(name)
        try:
            self.log.debug(name + ": Publishing: \"" + topic + "\", \"" + message + "\"")
            client.connect(host)
            r = client.publish(topic, message)
            self.log.debug(name + ": Result: " + str(r))
            if r:
                client.disconnect()
        except Exception as e:
            self.log.error(name + ": Failed to publish message to: " + host + " got error:\n\t" + str(e))

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

    log.info("Running standalone, testing " + __name__ + " sender")

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

    result = 200
    querytype = "phone"
    token = "+3580000"
    email = "gatekeeper@example.com"
    firstName = "Gatekeeper"
    lastName = "Testuser"
    nick = "Gatekeeper Test"
    phone = "+3580000"

    Mqtt.send(result, querytype, token, email, firstName, lastName, nick, phone)
    Mqtt.stop()
    
    log.info("Testing finished")