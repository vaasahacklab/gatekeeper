#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import json
import requests             # HTTP library
from urllib.parse import urlencode
from time import sleep

__all__ = ["urllog"]

class urllog:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.server_list = []

    def start(self, config):
        # Read urllog settings from global config and store needed data in module-wide table
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
            #headers = {'Content-Type': 'text/plain; charset=UTF-8',}
            message = urlencode({'key': api_key, 'phone': tokenid, 'message': membername,})
            r = requests.post(api_url, message, timeout=5)
            if r.status_code == requests.codes.ok:
                self.log.debug(name + ": Success, got answer: " + str(r.status_code) + " " + str(r.reason))
        except Exception as e:
            self.log.error(name + ": Failed to connect to: " + api_url + " got error:\n  " + str(e))

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

    log.debug("Testing urllog")
    urllog = urllog()
    urllog.start(config)
    urllog.send("00000000", "Urllog ÖÄäö")