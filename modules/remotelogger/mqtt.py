#!/usr/bin/env python3

import logging
import paho.mqtt.client as paho
from threading import Thread

__all__ = ["Mqtt"]

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
                self.log.info(server['name'] + ": Sending data")
                if server['staff']:
                    if 200 <= result <= 299:
                        data = {'querytype': querytype, 'token': token, 'email': email, 'firstName': firstName, 'lastName': lastName, 'nick': nick, 'phone': phone}
                    elif 400 <= result <= 499:
                        if result == 480:
                            data = {'querytype': querytype, 'token': token, 'nick': "NO_MEMBER_DENIED"}
                        elif result == 481:
                            data = {'querytype': querytype, 'token': token, 'nick': "MEMBER_DENIED"}
                        else:
                            data = {'querytype': querytype, 'token': token, 'nick': "DENIED"}
                    else:
                        data = None
                else:
                    if 200 <= result <= 299:
                        data = {'nick': nick}
                    elif 400 <= result <= 499:
                        data = {'nick': "DENIED"}
                    else:
                        data = None
                if data:
                    for key in data:
                        topic = "Gatekeeper/door/" + str(key)
                        message = str(data[key])
                        t = Thread(name=__name__ + ": " + server['name'], target=self._send, args=(server['name'], server['host'], topic, message))
                        thread_list.append(t)
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
        level=logging.DEBUG,
        format="%(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger(__name__)

    log.info("Running standalone, testing \"" + __name__ + "\" Gatekeeper remotelogger module")

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
        for key in config['remotelogger'][__name__.lower()]:
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