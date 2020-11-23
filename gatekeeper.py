#!/usr/bin/env python3

import os                   # To call external stuff on OS level
import sys                  # System calls
#import threading            # For enabling multitasking
#import json                 # JSON parser, for config file
import importlib            # Module loading
import logging, logging.config

# Create logs -folder if not exist
if not os.path.isdir(os.path.join(sys.path[0], "logs")):
    os.mkdir(os.path.join(sys.path[0], "logs"), 0o755)

logging.config.fileConfig("logging.ini")
log = logging.getLogger("Gatekeeper")

class Trigger:
    def __init__(self, config):
        log.debug("Initializing trigger modules")
        self.available_modules = []
        self.usable_modules = []
        for key in config['trigger']:
            modulename = key.lower()
            log.info("Importing trigger module: \"" + modulename + "\"")
            try:
                module = importlib.import_module(modulename)
                self.available_modules.append(module)
            except Exception as e:
                log.warning("Failed to import trigger module \"" + modulename + "\", got error:\n\t" + str(e))
        for item in self.available_modules:
            configlist = []
            for key in config['trigger'][item.__name__]:
                configlist.append(key)
            try:
                self.usable_modules.append(item.Gatekeeper(configlist))
            except Exception as e:
                log.warning("Failed to load trigger module: \"" + module.__name__ + "\", error:\n\t" + str(e))
        if not self.usable_modules:
            error = "Need at least one trigger module!"
            log.critical(error)
            #raise ImportError(error)

class Query:
    def __init__(self, config):
        log.debug("Initializing query modules")
        self.available_modules = []
        self.usable_modules = []
        for key in config['query']:
            modulename = key.lower()
            log.info("Importing query module: \"" + modulename + "\"")
            try:
                module = importlib.import_module(modulename)
                self.available_modules.append(module)
            except Exception as e:
                log.warning("Failed to import query module \"" + modulename + "\", got error:\n\t" + str(e))
        for item in self.available_modules:
            configlist = []
            for key in config['query'][item.__name__]:
                configlist.append(key)
            try:
                self.usable_modules.append(item.Gatekeeper(configlist))
            except Exception as e:
                log.warning("Failed to load query module: \"" + module.__name__ + "\", error:\n\t" + str(e))
        if not self.usable_modules:
            error = "Need at least one query module!"
            log.critical(error)
            #raise ImportError(error)

class Action:
    def __init__(self):
        moduleclass = __class__.__name__.lower()
        log.debug("Initializing " + moduleclass + " modules")
        directory = os.path.join(sys.path[0], "modules", moduleclass)
        sys.path.insert(0, directory)
        self.modules = []
        for entry in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, entry)):
                if entry.endswith(".py"):
                    entry = entry.rstrip(".py")
                    log.info("Importing " + moduleclass + " module: \"" + entry + "\"")
                    try:
                        module = importlib.import_module(entry)
                        self.modules.append(module.Gatekeeper())
                    except Exception as e:
                        log.warning("Failed to import " + moduleclass + " module \"" + entry + "\", got error:\n\t" + str(e))
        sys.path.remove(directory)
        if not self.modules:
            error = "At least one working " + moduleclass + " module is required!"
            log.critical(error)
            raise ImportError(error)




class Remotelogger:
    def __init__(self, config):
        log.debug("Initializing Remotelogger modules")
        self.available_modules = []
        self.usable_modules = []
        for key in config['remotelogger']:
            modulename = key.lower()
            log.info("Importing Remotelogger module: \"" + modulename + "\"")
            try:
                module = importlib.import_module(modulename)
                self.available_modules.append(module)
            except Exception as e:
                log.warning("Failed to import Remotelogger module \"" + modulename + "\", got error:\n\t" + str(e))
        for item in self.available_modules:
            configlist = []
            for key in config['remotelogger'][item.__name__]:
                configlist.append(key)
            try:
                getmodule = item.Gatekeeper(configlist)
                self.usable_modules.append(getmodule)
            except Exception as e:
                log.warning("Failed to load Remotelogger module: \"" + module.__name__ + "\", error:\n\t" + str(e))
        if not self.usable_modules:
            log.warning("No working Remotelogger modules!")

class Gatekeeper:
    def __init__(self):
        log.info("Starting Gatekeeper")
        # Add module folders into python path, so module importer can find them
        #sys.path.append(os.path.join(sys.path[0], "modules", "trigger"))
        #sys.path.append(os.path.join(sys.path[0], "modules", "query"))
        #sys.path.append(os.path.join(sys.path[0], "modules", "remotelogger"))
        #self.trigger = Trigger(config)
        #self.query = Query(config)
        self.action = Action()
        #self.remotelogger = Remotelogger(config)

    def start(self):


        result = 200
        querytype = "phone"
        token = "+3580000"
        email = "gatekeeper@example.com"
        firstName = "Gatekeeper"
        lastName = "Testuser"
        nick = "Gatekeeper Test"
        phone = "+3580000"

        for module in self.action.modules:
            module.send(result, querytype, token, email, firstName, lastName, nick, phone)
#        for module in self.remotelogger.usable_modules:
#            module.send(result, querytype, token, email, firstName, lastName, nick, phone)

    def stop(self):
        log.info("Stopping Gatekeeper")
        for module in self.action.modules:
            module.stop()

gatekeeper = Gatekeeper()
gatekeeper.start()
gatekeeper.stop()
