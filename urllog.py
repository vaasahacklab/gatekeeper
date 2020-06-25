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
        self.result = {}

        # Read urllog settings from global config and build thread list per instance
        for key, value in config.items():
            if key.upper() == "URLLOG":
                for section in value:
                    self.server_list.append(section)
        if not self.server_list:
            self.log.info("No \"" + __name__ + "\" config parameters found, nothing to do.")

    def send(self, nick, token):
        for server in self.server_list:
            t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['api_url'], server['api_key'], nick, token))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()

    def waitSendFinished(self):
        for thread in self.thread_list:
            thread.join()
        
    def _send(self, name, url, key, nick, token):
        self.result[name] = None
        content = {'key': key, 'message': nick, 'number': token}
        self.log.info(name + ": Sending token: \"" + str(token) + "\", nick: \"" + str(nick) +"\"")
        try:
            r = requests.post(url, data=content, timeout=(5, 15))
            if r:
                self.log.debug(name + ": HTTP responsecode: " + str(r.status_code))
            else:
                self.log.error(name + ": Failed to send message to: " + url + ", got HTTP status: " + str(r.status_code))
            self.result[name] = r.status_code
        except Exception as e:
            self.log.error(name + ": Failed to send message to: " + url + " with error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json
    from threading import Thread

    __name__ = "urllog"

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

    log.info("Running standalone, testing urllog sender")

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
    
    Urllog.send(nick="Gatekeeper testmessage", token="+3580000")
    Urllog.waitSendFinished()

    log.info("Results:")
    for server in Urllog.server_list:
        if not Urllog.result[server['name']]:
            log.info(str(server['name']) + ": Other error, see error logs above")
        elif Urllog.result[server['name']] == 200:
            log.info(str(server['name']) + ": Message sent successfully")
        elif Urllog.result[server['name']] == 403:
            log.info(str(server['name']) + ": Error: 403 Forbidden, check api_key")
        elif Urllog.result[server['name']] == 404:
            log.info(str(server['name']) + ": Error: 404 Not found, check api_url")
        else:
            log.info(str(server['name']) + ": Error: Got unknown error code: \"" + str(Urllog.result[server['name']]) + "\"")
    log.info("Testing finished")