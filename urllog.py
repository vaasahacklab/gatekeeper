#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import requests

__all__ = ["Urllog"]

class Urllog:
    def __init__(self):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []

    def start(self, config):
        # Read Matrix settings from global config and store needed data in module-wide table
        for key, value in config.items():
            if key.upper() == "URLLOG":
                for section in value:
                    self.server_list.append(section)

    def stop(self):
        for thread in self.thread_list:
            thread.join()

    def send(self, message, number):
        for server in self.server_list:
            t = threading.Thread(name=__name__ + ": " + server['name'], target=self.send_message, args=(server['name'], server['url'], server['key'], message, number))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()
        
    def send_message(self, name, url, key, message, number):
        url = "https://" + url
        data = {'key': key, 'number': number, 'message': message}
        self.log.info(name + ": Sending number: \"" + str(number) + "\", message: \"" + str(message) + "\" to: " + url)
        try:
            r = requests.post(url, data, timeout=(5, 15))
            self.log.debug(name + ": Result: " + str(r))
        except Exception as e:
            self.log.error(name + ": Failed to send message to: " + url + " got error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json
    import requests

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

    log.info("Testing urllog sender")
    Urllog = Urllog()
    Urllog.start(config)
    Urllog.send(message="Gatekeeper Urllog testmessage", number="+358000000000")
    Urllog.stop()
