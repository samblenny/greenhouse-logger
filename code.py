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
#
from board import D9, D10, SPI
from micropython import const
from time import sleep


def main():
    # This will run each time the board wakes from deep sleep.

    print("greetings. I'm awake now.")
