#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, logging.config
logging.config.fileConfig("logging.ini")

import os
import sys
import json

import mulysa
import urllog
#import matrix
import mqtt

log = logging.getLogger("Gatekeeper")

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

class Gatekeeper:
    def __init__(self, config):
        log.debug("Initialising Gatekeeper")
        self.Mulysa = mulysa.Mulysa(config)
        #self.Modem = Modem.Modem()
        self.Urllog = urllog.Urllog(config)
        #self.Matrix = matrix.Matrix(config)
        self.Mqtt = mqtt.Mqtt(config)

    def startModules(self):
        pass
        #self.Modem.start(config)
        #self.Matris.start(config)

    def stopModules(self):
    	pass
        #self.Modem.stop()
        #self.Matrix.stop()

    def sendData(self, result, querytype, token, email=None, firstName=None, lastName=None, nick=None, phone=None):
        if 200 <= result <= 299:
            self.Mqtt.send("door/name", nick)
            self.Urllog.send(nick, token)
        elif result == 480:
            self.Mqtt.send("door/name", "DENIED")
            self.Urllog.send("DENIED", token)
        elif result == 481:
            self.Mqtt.send("door/name", "DENIED")
            self.Urllog.send("DENIED", token)

    def waitDataSendFinished(self):
        self.Mqtt.waitSendFinished()
        self.Urllog.waitSendFinished()

    def queryToken(self, querytype, token):
        self.Mulysa.query(querytype, token)
        self.Mulysa.waitQueryFinished()

    def handleResults(self, querytype, token):
        for server in self.Mulysa.server_list:
            result = self.Mulysa.queryResult[server['name']]
            log.debug("Query response: " + str(result))
            if not result:
                log.error("Did not get response from \"" + str(server['name']) + "\"")
            elif 200 <= result[0] <= 299:
                log.info("Successful response from \"" + str(server['name']) + "\"")
                data = json.loads(result[1])
                log.debug("Email: " + str(data['email']))
                log.debug("First Name: " + str(data['first_name']))
                log.debug("Last Name: " + str(data['last_name']))
                log.debug("Nick: " + str(data['nick']))
                log.debug("Phone: " + str(data['phone']))

                if not data['nick']:
                    data['nick'] = str(data['first_name'][0] + "." + data['last_name'][0] + ".")

                # Do open door here
                self.sendData(result[0], querytype, token, str(data['email']), str(data['first_name']), str(data['last_name']), str(data['nick']), str(data['phone']))
                # Wait door to finish here
                self.waitDataSendFinished()

            elif result[0] == 480:
                log.info("No \"" + str(querytype) + "\" token of \"" + str(token) + "\" exist on \"" + str(server['name']) + "\"")
                self.sendData(result[0], querytype, token)
                self.waitDataSendFinished()
            elif result[0] == 481:
                log.info("\"" + str(token) + "\" token exist on \"" + str(server['name']) + "\", but member has no door access")
                self.sendData(result[0], querytype, token)
                self.waitDataSendFinished()
            elif result[0] == 404:
                log.error("Device_id \"" + str(server['device_id']) + "\" or token type \"" + str(token) + "\" is invalid")
            else:
                log.error("Unknown error, HTTP code: " + str(result[0]) + ", possible response message:\n\t" + str(result[1]))

    def start(self):
        log.info("Starting Gatekeeper")
        tokentype = "phone"
        tokenitself = "+3580002"
        self.queryToken(tokentype, tokenitself)
        self.handleResults(tokentype, tokenitself)

        self.stop()

    def stop(self):
        log.debug("Stopping")
        self.stopModules()
        log.info("Stopped")

gatekeeper = Gatekeeper(config)
gatekeeper.start()