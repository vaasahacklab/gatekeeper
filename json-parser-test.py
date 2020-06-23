#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os                   # To call external stuff
import sys                  # System calls
#import threading            # For enabling multitasking
import json                 # JSON parser, for config file
from time import sleep
import mqtt
import urllog

# Load configuration file
print("Loading config file")
try:
    with open(os.path.join(sys.path[0], "config.json"), "r") as f:
        config = json.load(f)
    f.close()
except Exception as e:
    print("Failed loading config file: " + str(e))
    raise e

class JsonParserTest:
    def __init__(self, config):
        print("Initialising JSON Parser Tester")

    def start(self):
        print("config JSON-dump:\n\n")
        print(json.dumps(config, indent=4, ensure_ascii=False) + "\n\n")

        print("per key:\n\n")
        for key in config:
            print(key)
        print("\n\n")

        print("per key, value:\n\n")
        for key, value in config.items():
            print(" " + str(key) + str(value) + "\n")
        print("\n\n")

        print("key in matrix:\n\n")
        for key in config['matrix']:
            print(key)
        print("\n\n")

        print("key in matrix->bot:\n\n")
        for key, value in config['matrix'].items():
            if key.upper() == "BOT":
                print(value)
        print("\n\n")

        print("matrix->bot, values:\n\n")
        for key in config['matrix']['bot']:
                print(key + ": " + config['matrix']['bot'][key])
        print("\n\n")

        print("if matrix->bot has default session_id value (starts with \"this\"), change it to \"success!\", in memory")
        if config['matrix']['bot']['session_id'].upper().split()[0] == "THIS":
            original=config['matrix']['bot']['session_id']
            print("Before: " + config['matrix']['bot']['session_id'])
            config['matrix']['bot']['session_id'] = "success!"
            print("After: " + config['matrix']['bot']['session_id'])
            config['matrix']['bot']['session_id'] = original
            print("Back to original: " + config['matrix']['bot']['session_id'])
        print("\n\n")

        print("if matrix->bot has default access token value (starts with \"this\"), change it to \"success!\", into test file configtest.json")
        if config['matrix']['bot']['accesstoken'].upper().split()[0] == "THIS":
            config['matrix']['bot']['accesstoken'] = "success!"
        print("Saving configtest.json")
        with open(os.path.join(sys.path[0], "configtest.json"), "w") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        f.close()
        print("\nLoad configtest.json and print:\n\n")
        with open(os.path.join(sys.path[0], "configtest.json"), "r") as f:
            testconfig = json.load(f)
        f.close()
        print(json.dumps(testconfig, indent=4, ensure_ascii=False) + "\n\n")
        print("Deleting configtest.json")
        os.remove(os.path.join(sys.path[0], "configtest.json"))
        print("\n\n")

    def stop(self):
        print("stop")

jsonparsertest = JsonParserTest(config)
jsonparsertest.start()
jsonparsertest.stop()
