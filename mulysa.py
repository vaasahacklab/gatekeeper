#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests

__all__ = ["Mulysa"]

class Mulysa:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []
        self.result = {}

        # Read Mulysa settings from global config and build thread list per instance
        for key, value in config.items():
            if key.upper() == "MULYSA":
                self.server_list.append(value)
        if not self.server_list:
            self.log.warning("No " + __name__ + " config parameters found, nothing to do.")

    def query(self, querytype, querytoken):
        for server in self.server_list:
            t = Thread(name=__name__, target=self._query, args=(server['name'], server['host'], server['device_id'], querytype, querytoken))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()

    def waitQueryFinished(self):
        for thread in self.thread_list:
            thread.join()

    def _query(self, name, host, device_id, querytype, querytoken):
        self.result[name] = None
        try:
            url = host + "/api/v1/access/" + querytype + "/"
            content = {'deviceid': device_id, 'payload': querytoken}
            r = requests.post(url, json=content, timeout=5)
            self.log.debug("Query: HTTP responsecode: " + str(r.status_code))
            self.log.debug("Query: Response text: " + str(r.text))
            if r.status_code == requests.codes.ok:
                self.result[name] = [r.status_code, r.text]
            else:
                self.result[name] = [r.status_code]
        except Exception as e:
            self.log.error("Query failed to " + url + " with error:\n" + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json
    from threading import Thread

    if len(sys.argv) - 1 != 2:
        print("Usage: " + sys.argv[0] + " <querytype> <querytoken>")
        print("For example: " + sys.argv[0] + " phone +3580000")
        quit()

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

    log.info("Running standalone, testing Mulysa query")

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

    Mulysa = Mulysa(config)

    log.info("Testing live query")
    Mulysa.query(querytype=sys.argv[1], querytoken=sys.argv[2])
    Mulysa.waitQueryFinished()

    for server in Mulysa.server_list:
        if not Mulysa.result[server['name']]:
            log.error("Did not get response from \"" + server['name'] + "\"")
        elif 200 <= Mulysa.result[server['name']][0] <= 299:
            log.info("Successful response from \"" + server['name'] + "\", got:")
            data = json.loads(Mulysa.result[server['name']][1])
            log.info("Email: " + data['email'])
            log.info("First Name: " + data['first_name'])
            log.info("Last Name: " + data['last_name'])
            log.info("Nick: " + data['nick'])
            log.info("Phone: " + data['phone'])
        elif Mulysa.result[server['name']][0] == 480:
            log.info("No such \"" + sys.argv[1] + "\" token exist on \"" + server['name'] + "\"")
        elif Mulysa.result[server['name']][0] == 481:
            log.info("\"" + sys.argv[1] + "\" token exist on \"" + server['name'] + "\", but member has no door access")
        elif Mulysa.result[server['name']][0] == 404:
            log.error("Device_id \"" + server['device_id'] + "\" or token type \"" + sys.argv[1] + "\" is invalid")
