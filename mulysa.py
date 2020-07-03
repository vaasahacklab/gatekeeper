#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
from threading import Thread

__all__ = ["Mulysa"]

class Mulysa:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.query_list = []
        self.queryAccessList_list = []
        self.queryResult = {}
        self.queryAccessListResult = {}

        # Read Mulysa settings from global config and build thread list per instance
        for key, value in config.items():
            if key.upper() == "MULYSA":
                self.server_list.append(value)
        if not self.server_list:
            self.log.warning("No " + __name__ + " config parameters found, nothing to do.")

    def query(self, querytype, querytoken):
        for server in self.server_list:
            t = Thread(name=__name__, target=self._query, args=(server['name'], server['host'], server['device_id'], querytype, querytoken))
            self.query_list.append(t)
        for thread in self.query_list:
            thread.start()

    def waitQueryFinished(self):
        for thread in self.query_list:
            thread.join()

    def _query(self, name, host, device_id, querytype, querytoken):
        self.queryResult[name] = None
        try:
            url = host + "/api/v1/access/" + querytype + "/"
            content = {'deviceid': device_id, 'payload': querytoken}
            r = requests.post(url, json=content, timeout=5)
            self.log.debug("Query: HTTP responsecode: " + str(r.status_code))
            self.log.debug("Query: Response text: " + str(r.text))
            if r.status_code == requests.codes.ok:
                self.queryResult[name] = [r.status_code, r.text]
            else:
                self.queryResult[name] = [r.status_code]
        except Exception as e:
            self.log.error("Query failed to " + str(url) + " with error:\n" + str(e))

    def queryAccessList(self, querytype):
        for server in self.server_list:
            t = Thread(name=__name__, target=self._queryAccessList, args=(server['name'], server['host'], server['device_id'], querytype, server['accesstoken']))
            self.queryAccessList_list.append(t)
        for thread in self.queryAccessList_list:
            thread.start()

    def waitQueryAccessListFinished(self):
        for thread in self.queryAccessList_list:
            thread.join()

    def _queryAccessList(self, name, host, device_id, querytype, accesstoken):
        self.queryAccessListResult[name] = None
        try:
            url = host + "/api/v1/access/" + querytype + "/"
            headers = {'Authorization': 'Token ' + accesstoken}
            r = requests.get(url, headers=headers, timeout=15)
            self.log.debug("Query: HTTP responsecode: " + str(r.status_code))
            self.log.debug("Query: Response text: " + str(r.text))
            self.queryAccessListResult[name] = [r.status_code, r.text]
        except Exception as e:
            self.log.error("Access list query failed to " + str(url) + " with error:\n" + str(e))

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json

    commandLineArguments = len(sys.argv) - 1

    if commandLineArguments < 1 or commandLineArguments > 2:
        print("Usage: " + str(sys.argv[0]) + " <querytype> [querytoken]\n")
        print("For example:\n")
        print(str(sys.argv[0]) + " phone +3580000\n")
        print("OR\n")
        print(str(sys.argv[0]) + " phone\n")
        print("If querytoken is given, an live query of token is tested")
        print("If querytoken is omitted, an access list query is tested\n")
        quit()

    __name__ = "Mulysa"

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

    if commandLineArguments == 2:
        log.info("Running standalone, testing Mulysa live query")
    if commandLineArguments == 1:
        log.info("Running standalone, testing Mulysa access list query")

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

    if commandLineArguments == 2:
        Mulysa.query(querytype=str(sys.argv[1]), querytoken=str(sys.argv[2]))
        Mulysa.waitQueryFinished()

        for server in Mulysa.server_list:
            result = Mulysa.queryResult[server['name']]
            if not result:
                log.error("Did not get response from \"" + str(server['name']) + "\"")
            elif 200 <= result[0] <= 299:
                log.info("Successful response from \"" + str(server['name']) + "\", got:")
                data = json.loads(result[1])
                log.info("Email: " + str(data['email']))
                log.info("First Name: " + str(data['first_name']))
                log.info("Last Name: " + str(data['last_name']))
                log.info("Nick: " + str(data['nick']))
                log.info("Phone: " + str(data['phone']))
            elif result[0] == 480:
                log.error("No \"" + str(sys.argv[1]) + "\" token of \"" + str(sys.argv[2]) + "\" exist on \"" + str(server['name']) + "\"")
            elif result[0] == 481:
                log.error("\"" + str(sys.argv[1]) + "\" token exist on \"" + str(server['name']) + "\", but member has no door access")
            elif result[0] == 404:
                log.error("Device_id \"" + str(server['device_id']) + "\" or token type \"" + str(sys.argv[1]) + "\" is invalid")
            else:
                log.error("Unknown error, HTTP code: " + str(result[0]) + ", possible response message:\n\t" + str(result[1]))

    if commandLineArguments == 1:
        Mulysa.queryAccessList(querytype=str(sys.argv[1]))
        Mulysa.waitQueryAccessListFinished()

        for server in Mulysa.server_list:
            result = Mulysa.queryAccessListResult[server['name']]
            if not result:
                log.error("Did not get response from \"" + str(server['name']) + "\"")
            elif 200 <= result[0] <= 299:
                log.info("Successful response from \"" + str(server['name']) + "\", received access list")
            elif result[0] == 404:
                #log.error("Device_id \"" + str(server['device_id']) + "\" or token type \"" + str(sys.argv[1]) + "\" is invalid")
                log.error("Token type \"" + str(sys.argv[1]) + "\" is invalid")
            else:
                log.error("Unknown error, HTTP code: " + str(result[0]) + ", possible response message:\n\t" + str(result[1]))