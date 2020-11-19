#!/usr/bin/env python3

import logging
import requests
from threading import Thread

__all__ = ["Doorbell"]

class Gatekeeper:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.log.debug("Initializing")
        self.server_list = []

        # Config comes from main gatekeeper
        for key in config:
            self.server_list.append(key)
        if not self.server_list:
            self.log.error("No \"" + __name__ + "\" config parameters found.")

    def start(self):
        if self.server_list:
            self.log.debug("Starting")
            self.log.debug("Started")

    def send(self, result, querytype, token, email=None, firstName=None, lastName=None, nick=None, phone=None):
        if self.server_list:
            thread_list = []
            for server in self.server_list:
                if 200 <= result <= 299:
                    dooropened = True
                elif 400 <= result <= 499:
                    if result == 480:
                        dooropened = False
                    elif result == 481:
                        dooropened = False
                    else:
                        dooropened = None
                else:
                    dooropened = None
                if dooropened is not None:
                    self.log.info(server['name'] + ": Sending dingdong")
                    t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['url'], dooropened))
                    thread_list.append(t)
            if thread_list:
                for thread in thread_list:
                    thread.start()
                self.log.debug("Waiting threads to finish")
                for thread in thread_list:
                    thread.join()
                self.log.debug("Threads finished")

    def stop(self):
        if self.server_list:
            self.log.debug("Stopping")
            self.log.debug("Stopped")

    def _send(self, name, url, dooropened):
        content = {'dooropened': dooropened}
        print(str(url), str(dooropened), str(content))
        self.log.debug(name + ": Sending dindong with dooropened: \"" + str(dooropened) + "\", to url: \"" + str(url) +"\"")
        try:
            r = requests.put(url, json=content, timeout=(5, 15))
            if 200 <= r.status_code <= 299:
                self.log.debug(name + ": Dingdong sent successfully")
            elif r.status_code == 404:
                self.log.error(name + ": 404 Not found, check url")
            else:
                self.log.error(name + ": Got unknown error code: \"" + str(r.status_code) + "\", with possible response:\n\t" + str(r))
            r.connection.close()
        except Exception as e:
            self.log.error(name + ": Failed to send dingdong to: " + str(url) + " with error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json

    __name__ = "Doorbell"

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

    log.info("Running standalone, testing \"" + __name__ + "\" Gatekeeper action module")

    # Load config from Gatekeeper config file
    log.debug("Loading config file")
    try:
        with open(os.path.join(sys.path[0], "..", "..", "config.json"), "r") as f:
            config = json.load(f)
        f.close()
    except ValueError as e:
        f.close()
        log.critical("config.json is malformed, got error:\n\t" + str(e))
    except Exception as e:
        log.critical("Failed loading config file, got error:\n\t" + str(e))

    configlist = []
    try:
        for key in config['action'][__name__.lower()]:
            configlist.append(key)
    except KeyError as e:
        log.error("Config section for action \"" + __name__.lower() + "\" does not exist.")
        raise e

    def testdata(mockresult):
        if mockresult == 200:
            querytype = "phone"
            token = "+3580200"
            email = "GateTest_IsMember_HasAccess@example.com"
            firstName = "GatekeeperTest"
            lastName = "IsMember_HasAccess"
            nick = "GateTest_IsMember_HasAccess"
            phone = "+3580000"
        elif mockresult == 480:
            querytype = "phone"
            token = "+3580480"
            email = None
            firstName = None
            lastName = None
            nick = None
            phone = None
            #email = "GateTest_NotMember@example.com"
            #firstName = "GatekeeperTest"
            #lastName = "NotMember"
            #nick = "GateTest_NotMember"
            #phone = "+3580001"
        elif mockresult == 481:
            querytype = "phone"
            token = "+3580481"
            email = None
            firstName = None
            lastName = None
            nick = None
            phone = None
            #email = "GateTest_IsMember_NoAccess@example.com"
            #firstName = "GatekeeperTest"
            #lastName = "IsMember_NoAccess"
            #nick = "GateTest_IsMemberHasAccess"
            #phone = "+3580002"
        return (mockresult, querytype, token, email, firstName, lastName, nick, phone)

    module = Gatekeeper(configlist)
    module.send(*testdata(200))
    module.send(*testdata(480))
    module.send(*testdata(481))

    module.stop()
    
    log.info("Testing finished")

