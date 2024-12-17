# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
# This is a greenhouse temperature logger with code designed to run on a few
# different Adafruit ESP32-S3 boards that I had lying around.
#
# Hardware:
# - Adafruit Metro ESP32-S3 - 16 MB Flash, 8 MB PSRAM (#5500)
# - Adafruit QT Py ESP32-S3 - 8 MB Flash, No PSRAM (#5426)
# - Adafruit QT Py ESP32-S3 - 4 MB Flash, 2MB PSRAM (#5700)
# - Adafruit microSD Card BFF Add-On for QT Py and Xiao (#5683)
# - FAT formated microSD card
# - Waterproof 1-Wire DS18B20 Digital temperature sensor
#
# Pinouts:
# | Metro S3 | SD slot | 1-wire |
# | -------- | ------- | ------ |
# | ...      | ...     | ...    |
#
# | Qt Py S3 | SD slot | 1-wire |
# | -------- | ------- | ------ |
# | ...      | ...     | ...    |
#
# Related Documentation:
# - https://learn.adafruit.com/adafruit-metro-esp32-s3
# - https://learn.adafruit.com/adafruit-qt-py-esp32-s3
# - https://learn.adafruit.com/adafruit-microsd-card-bff
# - https://learn.adafruit.com/using-ds18b20-temperature-sensor-with-circuitpython
# - https://learn.adafruit.com/deep-sleep-with-circuitpython/overview
# - https://docs.circuitpython.org/en/stable/shared-bindings/alarm/
#
from alarm import (
    light_sleep_until_alarms, exit_and_deep_sleep_until_alarms, wake_alarm
)
from alarm.time import TimeAlarm
from board import D9, D10, SPI, LED
from digitalio import DigitalInOut, Direction
from micropython import const
from time import monotonic, sleep


def light_sleep(seconds):
    # Do a light sleep then return
    ta = TimeAlarm(monotonic_time=monotonic() + seconds)
    light_sleep_until_alarms(ta)

def deep_sleep(seconds):
    # Do a deep sleep, which will result in a reboot (does not return)
    ta = TimeAlarm(monotonic_time=monotonic() + seconds)
    exit_and_deep_sleep_until_alarms(ta)

def blink(led_pin, n=1):
    # Blink an LED pin the specified number (n) of times
    for _ in range(n):
        led_pin.value = True
        light_sleep(0.05)
        led_pin.value = False
        light_sleep(0.3)

def main():
    # This will run each time the board wakes from deep sleep.
    led = DigitalInOut(LED)
    led.switch_to_output(value=False)
    if wake_alarm:
        # Woke from Periodic Alarm
        # - TODO log a temperature reading
        blink(led, 2)
    else:
        # First boot (maybe check for RTC time being reasonable?)
        blink(led, 1)
    # Turn on the LED then deep sleep (which should turn off the LED)
    led.value = True
    light_sleep(1)
    deep_sleep(8)
    # This point should not be reachable (code.py restarts on wake from alarm)


main()
