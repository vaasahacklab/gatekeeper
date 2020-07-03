#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
import asyncio
from queue import Queue 
from threading import Thread
from nio import (
    AsyncClient,
    AsyncClientConfig,
    LoginResponse,
    MatrixRoom,
    RoomMessageText,
)
from nio.store import SqliteStore

__all__ = ["Matrixbot"]

class Matrixbot:
    def __init__(self, config):
        self.log = logging.getLogger(__name__.capitalize())
        self.server_list = []
        self.thread_list = []
        self.room_list = []
        self.message = []

        # Read Matrix settings from global config and store needed data in module-wide tables
        for key, value in config.items():
            if key == "matrixbot":
                if not os.path.exists(os.path.join(sys.path[0], "matrixbot")):
                    self.log.debug("Session store folder for doesn't exist, creating it.")
                    try: 
                        os.mkdir(os.path.join(sys.path[0], "matrixbot"), mode=0o700)
                    except OSError as e: 
                        log.critical("Could not create session store folder, got error:\n" + e)
                        quit()

                for section in value:
                    self.server_list.append(section)
                    for key2, value2 in section.items():
                        if key2 == "rooms":
                            for room in value2:
                                self.room_list.append(room)
        if not self.server_list:
            self.log.info("No \"" + __name__ + "\" config parameters found, nothing to do.")

    def start(self):
        self.log.debug("Starting")
        for server in self.server_list:
            q = Queue()
            self.message.append(q)
            t = Thread(name=__name__ + ": " + server['name'], target=self._start, args=(server['name'], server['mxid'], server['password'], server['homeserver'], server['session_name'], server['session_id'], server['accesstoken'], server['rooms'], q))
            self.thread_list.append(t)
        for thread in self.thread_list:
            thread.start()
        self.log.debug("Started")


    def stop(self):
        self.log.debug("Stopping")
        for queue in self.message:
            queue.put(None)
        for queue in self.message:
            queue.join()
        for thread in self.thread_list:
            thread.join()
        self.log.debug("Stopped")

    def send(self, result, querytype, token, email=None, firstName=None, lastName=None, nick=None, phone=None):
        for queue in self.message:
            queue.put((result, querytype, token, email, firstName, lastName, nick, phone))

    def generateMessage(self, staffroom, message):
        result = message[0]
        querytype = message[1]
        token = message[2]
        email = message[3]
        firstName = message[4]
        lastName = message[5]
        nick = message[6]
        phone = message[7]

        if staffroom:
            if 200 <= result <= 299:
                message = ("Gatekeeper: door access granted with: \"" + querytype + "\", token: \"" + token + "\".\n"
                        "Member data:\n"
                        "\tFirst name: \"" + firstName + "\"\n"
                        "\tLast name: \"" + lastName + "\"\n"
                        "\tNick: \"" + nick + "\"\n"
                        "\tEmail: \"" + email + "\"\n"
                        "\tPhone: \"" + phone + "\"\n"
                )
            elif result == 480:
                message = "Gatekeeper: door access denied with: \"" + querytype + "\", token: \"" + token + "\", no member exist with that token."
            elif result == 481:
                message = "Gatekeeper: door access denied with: \"" + querytype + "\", token: \"" + token + "\", member has no door access."
            else:
                message = None
        else:
            if 200 <= result <= 299:
                message = "Gatekeeper: Opened door for: \"" + nick + "\"."
            elif result == 480:
                message = "Gatekeeper: Someone is knocking on the door"
            elif result == 481:
                message = "Gatekeeper: Member without door access knocked the door."
            else:
                message = None
        return message

    def _start(self, name, mxid, password, homeserver, session_name, session_id, accesstoken, rooms, q):
        self.log.info(name + ": Logging in")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        clientConf = AsyncClientConfig(max_timeouts=2, request_timeout=10, store=SqliteStore)
        client = AsyncClient(homeserver=homeserver, user=mxid, store_path=os.path.join(sys.path[0], "matrixbot"), config=clientConf)
        loop.run_until_complete(self._start_(name, client, mxid, password, session_name, session_id, accesstoken, q))

    async def message_callback(self, room: MatrixRoom, event: RoomMessageText) -> None:
        print(
            f"Message received in room {room.display_name}\n"
            f"{room.user_name(event.sender)} | {event.body}"
        )

    async def _start_(self, name, client, mxid, password, session_name, session_id, accesstoken, q):
        for key, value in config.items():
            if key == "matrixbot":
                for section in value:
                    if section['name'] == name:
                        try:
                            if not section['accesstoken'].upper().split()[0] == "THIS":
                                self.log.debug(name + ": Restoring existing login")
                                client.restore_login(user_id=mxid, device_id=session_id, access_token=accesstoken)
                            elif section['accesstoken'].upper().split()[0] == "THIS":
                                self.log.debug(name + ": Trying password login")
                                resp = await client.login(password, session_name)
                                if (isinstance(resp, LoginResponse)):
                                    self.log.debug(name + ": Response: " + str(resp))
                                    self.log.debug(name + ": session_id: " + client.device_id)
                                    self.log.debug(name + ": accesstoken: " + client.access_token)
                                    self.log.info(name + ": Password login successful, saving session data")
                                    section['session_id'] = client.device_id
                                    section['accesstoken'] = client.access_token
                                    with open(os.path.join(sys.path[0], "config.json"), "w") as f:
                                        json.dump(config, f, indent=4, ensure_ascii=False)
                                    f.close()
                                else:
                                    self.log.debug(name + ": Failed to log in: " + str(resp))
                                    self.message.remove(q)
                                    return
                        except Exception as e:
                            self.log.error(name + ": Unknown exeption:\n" + str(e))
                            return
                        finally:
                            if client.should_upload_keys:
                                try:
                                    self.log.debug("Uploading E2E keys")
                                    await client.keys_upload()
                                except Exception as e:
                                    self.log.error(name + ": Error uploading keys:\n\t" + str(e))
                                    return
                            
                            try:
                                self.log.debug(name + ": Syncing state")
                                await client.sync(full_state=True, timeout=30000)
                                client.add_event_callback(self.message_callback, RoomMessageText)
                            except Exception as e:
                                self.log.error(name + ": Error starting sync loop:\n\t" + str(e))
                                return
                            finally:

                                while True:          
                                    message = q.get()
                                    if message is None:
                                        q.task_done()
                                        break

                                    try:
                                        for room in section['rooms']:
                                            parsedMessage = self.generateMessage(room['staffroom'], message)
                                            self.log.info(name + ": Sending message to room \"" + room['name'] + "\"")
                                            try:
                                                await client.room_send(
                                                    ignore_unverified_devices = False,
                                                    room_id = room['id'],
                                                    message_type="m.room.message",
                                                    content = {
                                                        "msgtype": "m.notice",
                                                        "body": parsedMessage
                                                    }
                                                )
                                            except Exception as e:
                                                    self.log.error(name + ": Couldn't send message to room \"" + room['name'] + "\", got error:\n\t" + str(e))
                                    finally:
                                        q.task_done()

                                await client.close()

# Test routine if module is run as standalone program instead of imported as module
if __name__ == "__main__":
    import os
    import sys
    import json

    __name__ = "Matrixbot"

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

    log.info("Running standalone, testing matrix sender")

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

    Matrixbot = Matrixbot(config)
    Matrixbot.start()

    result = 200
    querytype = "phone"
    token = "+3580000"
    email = "gatekeeper@example.com"
    firstName = "Gatekeeper"
    lastName = "Testuser"
    nick = "Gatekeeper Test"
    phone = "+3580000"

    log.debug("Sending testdata")    
    Matrixbot.send(result, querytype, token, email, firstName, lastName, nick, phone)
    Matrixbot.stop()
    log.info("Test finished")
