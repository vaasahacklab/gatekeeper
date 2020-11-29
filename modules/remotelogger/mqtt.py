#!/usr/bin/env python3

import os
import sys
import json
import logging
import paho.mqtt.client as paho
from queue import Queue
from threading import Thread

__all__ = ["Mqtt"]

class Gatekeeper:
    def __init__(self):
        self.log = logging.getLogger(__name__.capitalize())
        self.log.debug("Initializing")
        self.server_list = []
        self.thread_list = []
        self.message = []

        # Load config from file from json file with same module name
        self.log.debug("Loading config file " + __name__.lower() + ".json")
        try:
            with open(os.path.join(sys.path[0], __name__.lower() + ".json"), "r") as f:
                config = json.load(f)
            f.close()
        except ValueError as e:
            f.close()
            self.log.critical(__name__.lower() + ".json is malformed, got error:\n\t" + str(e))
            raise e
        except Exception as e:
            self.log.critical("Failed loading " + __name__.lower() + ".json, got error:\n\t" + str(e))
            raise e
        
        for key in config:
            self.server_list.append(key)
        if not self.server_list:
            self.log.error("No \"" + __name__ + "\" config parameters found.")
            sys.exit(1)

        for server in self.server_list:
            queue = Queue()
            self.message.append(queue)
            t = Thread(name=__name__ + ": " + server['name'], target=self._start, args=(server['name'], server['host'], server['staff'], queue))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()
        self.log.debug("Started")

    def _start(self, name, host, staff, queue):
        while True:          
            message = queue.get()
            if message is None:
                queue.task_done()
                break
            try:
                self._send(name, host, staff, message)
            except Exception as e:
                self.log.error(name + ": Couldn't publish to host \"" + host + "\", got error:\n\t" + str(e))
            finally:
                queue.task_done()

    def send(self, result, querytype, token, email=None, firstName=None, lastName=None, nick=None, phone=None):
        for queue in self.message:
            queue.put((result, querytype, token, email, firstName, lastName, nick, phone))

    def _waitthreads(self):
        self.log.debug("Waiting threads to finish")
        for thread in self.thread_list:
            thread.join()
        self.log.debug("Threads finished")

    def stop(self):
        self.log.debug("Stopping")
        for queue in self.message:
            queue.put(None)
        for queue in self.message:
            queue.join()
        self._waitthreads()
        self.log.debug("Stopped")

    def _send(self, name, host, staff, message):
        
        result = message[0]
        querytype = message[1]
        token = message[2]
        email = message[3]
        firstName = message[4]
        lastName = message[5]
        nick = message[6]
        phone = message[7]

        if staff:
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
            self.log.info(name + ": Publishing results")
            for key in data:
                topic = "Gatekeeper/door/" + str(key)
                message = str(data[key])
        
                client = paho.Client(name)
                try:
                    self.log.debug(name + ": Publishing: \"" + topic + "\", \"" + message + "\"")
                    client.connect(host)
                    r = client.publish(topic, message)
                    if r:
                        self.log.debug(name + ": topic: \"" + topic + "\" result " + str(r))
                        client.disconnect()
                except Exception as e:
                    self.log.error(name + ": Failed to publish message to: " + host + " got error:\n\t" + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
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

    log.info("Running standalone, testing \"" + __name__ + "\" Gatekeeper action module")

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
        elif mockresult == 481:
            querytype = "phone"
            token = "+3580481"
            email = None
            firstName = None
            lastName = None
            nick = None
            phone = None
            ## Support for "member but no dooraccess" style values will likely be supported on later Mulysa
            #email = "GateTest_IsMember_NoAccess@example.com"
            #firstName = "GatekeeperTest"
            #lastName = "IsMember_NoAccess"
            #nick = "GateTest_IsMemberHasAccess"
            #phone = "+3580002"
        return (mockresult, querytype, token, email, firstName, lastName, nick, phone)

    module = Gatekeeper()
    module.send(*testdata(200))
    module.send(*testdata(480))
    module.send(*testdata(481))

    module.stop()
    
    log.info("Testing finished")
    sys.exit(0)

