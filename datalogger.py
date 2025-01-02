# SPDX-License-Identifier: MIT
from board import board_id, A1, I2C
from digitalio import DigitalInOut
from micropython import const
from rtc import RTC
import time
from time import sleep

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from adafruit_max1704x import MAX17048


# Special value that gets recorded when there's a problem with the sensor
NO_DATA = const(0x80)

# Pin for the 1-wire bus
ONEWIRE_PIN = A1

# Singleton for the 1-wire bus object to avoid pin in use errors
_1WIRE = None


def has_max17():
    # Does this board have a MAX17048 battery fuel gauge? (return True/False)
    return board_id in (
        'adafruit_metro_esp32s3',
        'adafruit_feather_esp32s3_nopsram',
    )

def has_A3_divider():
    # Does this board have a battery voltage divider on A3? (return True/False)
    return board_id in (
        'adafruit_qtpy_esp32s3_4mbflash_2mbpsram',
        'adafruit_qtpy_esp32s3_nopsram',
    )

def battery_centivolts():
    # Return battery voltage (cV), or None if measurement is unavailable.
    # Note that 3.70V = 370cV, 4.19V = 419cV, etc. Using centi-Volts makes it
    # more convenient to send the voltage measurement in Morse code.
    cV = None
    if has_max17():
        with I2C() as i2c:
            max17 = MAX17048(i2c)
            max17.wake()
            sleep(0.5)
            cV = round(max17.cell_voltage * 100)
    elif has_A3_divider():
        pass
    return cV

def temp_f():
    # Return a temperature measurement in Fahrenheit (int8)
    global _1WIRE
    if not _1WIRE:
        _1WIRE = OneWireBus(ONEWIRE_PIN)
    # Loop over all devices on the 1-wire bus
    F = NO_DATA
    for d in _1WIRE.scan():
        if d.family_code != 0x28:
            # Skip devices that don't have the DS18B20 family code
            continue
        # Return temperature of first DS18B20, converting ¡C to ¡F
        ds18b20 = DS18X20(_1WIRE, d)
        F = round((ds18b20.temperature * 1.8) + 32)
    return F
