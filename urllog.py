#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests

__all__ = ["Urllog"]

class Urllog:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []

        # Read urllog settings from global config and build thread list per instance
        for key, value in config.items():
            if key.upper() == "URLLOG":
                for section in value:
                    self.server_list.append(section)
        if not self.server_list:
            self.log.info("No " + __name__ + " config parameters found, nothing to do.")

    def send(self, nick, token):
        for server in self.server_list:
            t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['api_url'], server['api_key'], nick, token))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()
        for thread in self.thread_list:
            thread.join()
        
    def _send(self, name, url, key, nick, token):
        content = {'key': key, 'nick': nick, 'token': token}
        self.log.info(name + ": Sending token: \"" + str(token) + "\", nick: \"" + str(nick) +"\"")
        try:
            r = requests.post(url, data=content, timeout=(5, 15))
            if r:
                self.log.debug(name + ": HTTP responsecode: " + str(r.status_code))
                self.log.info("Success")
            else:
                self.log.error(name + ": Failed to send message to: " + url + ", got HTTP status: " + str(r.status_code))
        except Exception as e:
            self.log.error(name + ": Failed to send message to: " + url + " with error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json
    from threading import Thread

    # Setup logging as we are standalone
    import logging.config
    logging.config.fileConfig("logging.ini")
    log = logging.getLogger(__name__)

    # Load config from file as we are standalone
    log.debug("Loading config file")
    try:
        with open(os.path.join(sys.path[0], "config.json"), "r") as f:
            config = json.load(f)
        f.close()
    except Exception as e:
        log.critical("Failed loading config file: " + str(e))
        raise e

    log.info("Running standalone, testing urllog sender")
    Urllog = Urllog(config)
    Urllog.send(nick="Gatekeeper testmessage", token="+3580000")
