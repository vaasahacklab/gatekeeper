#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import requests

__all__ = ["Matrix"]

class Matrix:
    def __init__(self):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []

    def start(self, config):
        # Read Matrix settings from global config and store needed data in module-wide table
        for key, value in config.items():
            if key.upper() == "MATRIX":
                for section in value:
                    self.server_list.append(section)

    def stop(self):
        for thread in self.thread_list:
            thread.join()

    def send(self, payload, number):
        for server in self.server_list:
            t = threading.Thread(name="Matrix-" + server['name'], target=self.send_message, args=(server['name'], server['host'], server['room'], server['token'], server['sendnumber'], payload, number))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()
        
    def send_message(self, name, host, room, token, sendnumber, payload, number):
        client = requests(name)
        try:
            url = 'https://' + host + '/_matrix/client/r0/rooms/' + room + '/send/m.room.message'
            msgtype = 'm.notice'
            self.log.debug(name + ": Sending Matrix message: \"" + payload + "\" to host: " + host)
            if sendnumber = True
                client.post(url, headers=headers={'Authorization': 'Bearer ' + token}, json={'msgtype': msgtype, 'body': payload, + ' number: ' + number})
            else
                client.post(url, headers=headers={'Authorization': 'Bearer ' + token}, json={'msgtype': msgtype, 'body': payload})
        except Exception as e:
            self.log.error(name + ": Failed to send message to: " + host + " got error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os                   # To call external stuff
    import sys                  # System calls
    import json                 # For parsing config file
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

    log.debug("Testing matrix")
    Matrix = Matrix()
    Matrix.start(config)
    Matrix.send("Matrix testmessage", '+358000000000')
    Matrix.stop()

