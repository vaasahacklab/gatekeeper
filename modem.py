#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import serial
import re

__all__ = ["Modem"]

log = logging.getLogger("Modem")

class Modem:
    def __init__(self):

        # Setup linestatus thread
        linestatus_loop = False
        self.linestatus = threading.Thread(target=self.linestatus, args=())

        # Setup GPIO pins used with modem
        # Read GPIO pin numbers from config file
        power = config["modem"]["gpio"]["power"]
        reset = config["modem"]["gpio"]["reset"]

        # Use RPi BOARD pin numbering convention
        GPIO.setmode(GPIO.BOARD)

        # Power button
        GPIO.setup(power, GPIO.OUT, initial = GPIO.LOW)
        log.debug("initialized power pin, pull to low")

        # Reset button
        GPIO.setup(reset, GPIO.OUT, initial = GPIO.LOW)
        log.debug("initialized reset pin, pull to low")

    def enable_caller_id(self):
        self.write_line("AT+CLIP=1")
        log.info("Enabled caller ID")

    def hangup(self):
        self.write_line("AT+HVOIC") # Disconnect only voice call
        log.debug("We hung up")

    def power_on(self):
        log.debug("Opening " + config["modem"]["port"])
        channel = serial.Serial(
            port = config["modem"]["port"],
            baudrate = config["modem"]["baudrate"],
            parity = config["modem"]["parity"],
            stopbits = config["modem"]["stopbits"],
            bytesize = config["modem"]["bytesize"],
            xonxoff = config["modem"]["xonxoff"],
            rtscts = config["modem"]["rtscts"],
            dsrdtr = config["modem"]["dsrdtr"],
            timeout = None,
            writeTimeout = 1
        )
        channel.write("AT"+"\r\n").encode("ascii")
        channel.readline()
        buffer = channel.readline()
        if not buffer:
            log.info("Powering on modem")
            GPIO.output(power, GPIO.HIGH)
            while True:
                line = channel.readline().strip()
                if line == "RDY":
                    log.info("Modem powered on")
                    break
            GPIO.output(modem_power, GPIO.LOW)
        log.debug("Waiting modem to be call ready")
        while True:
            line = channel.readline().strip()
            if line == "Call Ready":
                log.info("Modem call ready")
                break
        else:
            log.info("Modem already powered")

    def power_off(self):
        channel.write("AT"+"\r\n").encode("ascii")
        channel.readline()
        buffer = channel.readline()
        if not buffer:
            log.info("Modem already powered off")
        else:
            log.info("Powering off modem")
            GPIO.output(power, GPIO.HIGH)
            while True:
                line = channel.readline().strip()
                if line == "NORMAL POWER DOWN":
                    log.info("Modem powered off")
                    break
        GPIO.output(power, GPIO.LOW)
        channel.close()

    def reset(self):
        log.error("Modem has jammed, trying reset")
        log.debug("Resetting modem")
        GPIO.output(reset, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(reset, GPIO.LOW)
        log.debug("Modem reset done")

    def linestatus(self):
        self.linestatus_loop = True
        do_it = time.time()     # Set execute loop timing variable to "now"
        log.debug("Started linestatus check")
        while self.linestatus_loop:
            if time.time() > do_it:   # Execute these only if "now" is more than timing variable
                self.channel.isOpen()
                self.channel.write("AT+CREG?"+"\r\n")
                do_it = time.time() + 60  # Set timing variable 60 seconds from "now"
            time.sleep(1)
        log.debug("Stopped linestatus check")

    def write_line(self, line):
        line = (line + "\r\n").encode("ascii")
        try:
            self.channel.write(line)
        except Exception as e:
            log.debug("Write error", exc_info=e)
            self.close_channel()

    def read_channel(self):
        call_id_pattern = re.compile('^\+CLIP: *"(\d*?)"')
        creg_pattern = re.compile('\+CREG: *\d,[^125]')
        while True:
            buffer = self.channel.readline()
            call_id_match = call_id_pattern.match(buffer)

            if call_id_match:
                number = call_id_match.group(1)
                self.handle_call(number)

            if creg_pattern.match(buffer):
                log.error("Not connected with line \n"+buffer)
                self.reset()

    def close_channel(self):
        self.channel.close()
        self.channel = None

    def start(self):
        self.power_on()
        self.enable_caller_id()
        self.linestatus.start()

    def stop(self):
        self.linestatus_loop = False
        self.linestatus.join()
        self.close_channel()