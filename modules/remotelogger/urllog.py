#!/usr/bin/env python3

import os
import sys
import json
import logging
import requests
from queue import Queue
from threading import Thread

__all__ = ["Urllog"]

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
            t = Thread(name=__name__ + ": " + server['name'], target=self._start, args=(server['name'], server['url'], server['apikey'], server['staff'], queue))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()
        self.log.debug("Started")

    def _start(self, name, url, apikey, staff, queue):
        while True:          
            message = queue.get()
            if message is None:
                queue.task_done()
                break
            try:
                self._send(name, url, apikey, staff, message)
            except Exception as e:
                self.log.error(name + ": Couldn't send dindong to url \"" + url + "\", got error:\n\t" + str(e))
            finally:
                queue.task_done()

    def send(self, result, querytype, token, email=None, firstName=None, lastName=None, nick=None, phone=None):
        for queue in self.message:
            queue.put((result, token, nick))

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

    def _send(self, name, url, apikey, staff, message):
        
        result = message[0]
        token = message[1]
        nick = message[2]

        if staff:
            if 200 <= result <= 299:
                pass
            elif 400 <= result <= 499:
                if result == 480:
                    nick = "DENIED"
                elif result == 481:
                    nick = "DENIED"
                else:
                    nick = "DENIED"
        else:
            token = None
            if 200 <= result <= 299:
                pass
            elif 400 <= result <= 499:
                nick = "DENIED"

        if token:
            self.log.debug(name + ": Sending token: \"" + str(token) + "\", message: \"" + str(nick) +"\"")
            content = {'token': token, 'message': nick}
        else:
            self.log.debug(name + ": Sending message: \"" + str(nick) +"\"")
            content = {'message': nick}

        try:
            headers = {'Authorization': 'Bearer ' + apikey}
            r = requests.post(url, headers=headers, data=content, timeout=(5, 15))
            if 200 <= r.status_code <= 299:
                self.log.debug(name + ": Message sent successfully")
            elif r.status_code == 403:
                if r.reason:
                    self.log.error(name + ": 403 Forbidden, check apikey, got reason:\n\t" + str(r.reason))
                else:
                    self.log.error(name + ": 403 Forbidden, check apikey, no reason provided")
            elif r.status_code == 404:
                if r.reason:
                    self.log.error(name + ": Got 404 Not found, check url, with reason:\n\t" + str(r.reason))
                else:
                    self.log.error(name + ": Got 404 Not found, check url, no reason sent")
            else:
                if r.reason:
                    self.log.error(name + ": Got unexpected error code: \"" + str(r.status_code) + "\", with reason:\n\t" + str(r.reason))
                else:
                    self.log.error(name + ": Got unexpected error code: \"" + str(r.status_code) + "\", no reason sent")
            r.connection.close()
        except Exception as e:
            self.log.error(name + ": Failed to send message to: " + str(url) + " with error:\n  " + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
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

