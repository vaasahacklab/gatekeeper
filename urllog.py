#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
from threading import Thread

__all__ = ["Urllog"]

class Urllog:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []

        # Read urllog settings from global config and build thread list per instance
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
                        message = nick
                    elif result == 480:
                        message = "DENIED"
                    elif result == 481:
                        message = "DENIED"
                    else:
                        message = None
                else:
                    if 200 <= result <= 299:
                        token = None
                        message = nick
                    elif result == 480:
                        token = None
                        message = "DENIED"
                    elif result == 481:
                        token = None
                        message = "DENIED"
                    else:
                        message = None
            if message:
                t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['api_url'], server['api_key'], token, message))
                self.thread_list.append(t)
                for thread in self.thread_list:
                    thread.start()

    def stop(self):
        if self.server_list:
            self.log.debug("Stopping")
            self.waitSendFinished()
            self.log.debug("Stopping")

    def waitSendFinished(self):
        for thread in self.thread_list:
            thread.join()
        
    def _send(self, name, url, api_key, token, message):
        headers = {'Authorization': 'Bearer ' + api_key}
        content = {'token': token, 'message': message}
        self.log.debug(name + ": Sending token: \"" + str(token) + "\", message: \"" + str(message) +"\"")
        try:
            r = requests.post(url, headers=headers, data=content, timeout=(5, 15))
            if r.status_code == 200:
                self.log.debug(name + ": Message sent successfully")
            elif r.status_code == 403:
                self.log.error(name + ": 403 Forbidden, check api_key")
            elif r.status_code == 404:
                self.log.error(name + ": 404 Not found, check api_url")
            else:
                self.log.error(name + ": Got unknown error code: \"" + str(r.status_code) + "\", with possible response:\n\t" + str(r))
        except Exception as e:
            self.log.error(name + ": Failed to send message to: " + str(url) + " with error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json

    __name__ = "Urllog"

    # Setup logging to stdout
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
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

    Urllog = Urllog(config)

    result = 200
    querytype = "phone"
    token = "+3580000"
    email = "gatekeeper@example.com"
    firstName = "Gatekeeper"
    lastName = "Testuser"
    nick = "Gatekeeper Test"
    phone = "+3580000"

    Urllog.send(result, querytype, token, email, firstName, lastName, nick, phone)
    Urllog.stop()

    log.info("Testing finished")