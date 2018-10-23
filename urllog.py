#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os                   # To call external stuff
import sys                  # System calls
import threading
import json
import requests             # HTTP library
from time import sleep

__all__ = ["urllog"]

log = logging.getLogger(__name__)

log.debug("Loading config file...")
try:
    with open(os.path.join(sys.path[0], "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    log.error("Failed loading config file: " + str(e))
    raise e
log.debug("Config file loaded.")

class urllog:
    def __init__(self):
        self.server_list = []

        # Read urllog settings from global config json and store in module-wide table
        for key, value in config.items():
            if key == "urllog":
                for section in value:
                    self.server_list.append(section)

    def send(self, tokenid, membername):
        thread_list = []
        for server in self.server_list:
            t = threading.Thread(name="urllog-" + server['name'], target=self.send_to_server, args=(server['name'], server['api_url'], server['api_key'], tokenid, membername))
            thread_list.append(t)
        for thread in thread_list:
            thread.start()
        
    def send_to_server(self, name, api_url, api_key, tokenid, membername):
        try:
            data = {'key': api_key, 'phone': tokenid, 'message': membername}
            log.debug(name + ": POSTing: " + tokenid + " " + membername + " to: " + api_url)
            requests.post(api_url, data)
        except Exception as e:
            log.error(name + ": Failed to connect to: " + api_url + " got error:\n  " + str(e))

# Test routine if module is run as main program
if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig("logging.ini", disable_existing_loggers = False)

    log.debug("Testing urllog")
    urllog = urllog()
    urllog.send("00000000", "Urllog testmessage")