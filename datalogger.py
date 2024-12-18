# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
from alarm import (
    light_sleep_until_alarms, exit_and_deep_sleep_until_alarms
)
from alarm.time import TimeAlarm
import board
from digitalio import DigitalInOut
from neopixel_write import neopixel_write
from time import monotonic

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20


def sleep(seconds):
    # Do an ESP32 light sleep then return
    ta = TimeAlarm(monotonic_time=monotonic() + seconds)
    light_sleep_until_alarms(ta)

def deepsleep(seconds):
    # Do an ESP32 deep sleep, which does not return (alarm triggers reboot)
    ta = TimeAlarm(monotonic_time=monotonic() + seconds)
    exit_and_deep_sleep_until_alarms(ta)


class Datalogger:
    def __init__(self):
        # Initialize LED and 1-wire temp sensor
        qtpy_ids = (
            'adafruit_qtpy_esp32s3_nopsram',
            'adafruit_qtpy_esp32s3_4mbflash_2mbpsram',
        )
        b_id = board.board_id
        if b_id == 'adafruit_metro_esp32s3':
            # This board has an LED pin and neopixel power jumper (cut)
            self.has_led = True
            self.led = DigitalInOut(board.LED)
            self.led.switch_to_output(value=False)
        elif b_id in qtpy_ids:
            # These boards have NEOPIXEL_POWER pin but no LED pin
            self.has_led = False
            self.neo = DigitalInOut(board.NEOPIXEL)
            self.neopow = DigitalInOut(board.NEOPIXEL_POWER)
            #self.neo.switch_to_output(value=True)
            self.neopow.switch_to_output(value=False)

    def blink(self, n):
        # Blink LED pin or neopixel the specified number (n) of times
        slp_ = sleep
        t_on = 0.05
        t_off = 0.3
        if self.has_led:
            # Metro ESP32-S3 board with cut neopixel power: use red LED pin
            pin = self.led
            for _ in range(n):
                pin.value = True
                slp_(t_on)
                pin.value = False
                slp_(t_off)
        else:
            # Qt Py ESP32-S3 boards with neopixel power pin: use neopixel
            self.neopow.value = True
            slp_(0.01)  # wait 10ms for neopixel power to stabilize
            pin = self.neo
            color_on = bytearray([0, 5, 0])  # red (GRB order)
            color_off = bytearray([0, 0, 0])
            npw_ = neopixel_write
            for _ in range(n):
                npw_(pin, color_on)
                slp_(t_on)
                npw_(pin, color_off)
                slp_(t_off)
            self.neopow = False


    def measure(self):
        # Record a temperature measurement to ESP32-S3 sleep memory

        pass
        # TODO
        # Hardware:
        #  1. Wire bus with 4.7kΩ pull-up to 3.3 pin
        # Software:
        #  1. Read temperature
        #  2. Scale measurement to fit in 8 bits
        #  3. Scale timestamp to fit in 24 bits
        #  3. Save 32-bit [timestamp:temp] to alarm.sleep_memory[n:n+3]
