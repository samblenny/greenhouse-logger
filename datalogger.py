# SPDX-License-Identifier: MIT
from alarm import sleep_memory, light_sleep_until_alarms
from alarm.time import TimeAlarm
from board import board_id, I2C
from digitalio import DigitalInOut
from micropython import const
from rtc import RTC
from struct import pack, unpack
from time import monotonic
import time

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from adafruit_max1704x import MAX17048

from sleepmem import SleepMem


# Set this to True for additional debug prints
DEBUG = False

# Special value that gets recorded when there's a problem with the sensor
NO_DATA = 0x80


class Datalogger:

    def __init__(self, ow_pin):
        # Initialize 1-wire bus, temp sensor, sleep memory, and real time clock
        self.ow = OneWireBus(ow_pin)
        self.ds18b20 = self.find_ds18b20()
        self.sleepmem = SleepMem()
        self.rtc = RTC()

    def find_ds18b20(self):
        # Attempt to locate DS18B20 1-wire temp sensor
        if DEBUG:
            print("SCANNING 1-WIRE BUS:")
        for d in self.ow.scan():
            fam = d.family_code
            sn = d.serial_number
            if fam == 0x28:
                if DEBUG:
                    print(" fam:%02x, sn:%s" % (fam, sn.hex()))
                return DS18X20(self.ow, d)
        return None

    def record(self, tempF, batt):
        # Save timestamped measurements in ESP32 sleep memory.
        if (type(tempF) != int) or (tempF < -128) or (127 < tempF):
            tempF = NO_DATA
        if (type(batt) != int) or (batt < -20) or (120 < batt):
            batt = NO_DATA
        self.sleepmem.append_data(time.time(), tempF, batt)

    def measure_temp_f(self):
        # Return a temperature measurement in Fahrenheit (int8)
        if self.ds18b20:
            # .temperature is Celsius (float), so convert it
            return round((self.ds18b20.temperature * 1.8) + 32)
        return NO_DATA

    def batt_percent(self):
        # Check battery status on supported boards
        has_max17 = (
            'adafruit_metro_esp32s3',
            'adafruit_feather_esp32s3_nopsram',
        )
        if board_id in has_max17:
            with I2C() as i2c:
                max17 = MAX17048(i2c)
                max17.wake()
                seconds = 0.5
                light_sleep_until_alarms(
                    TimeAlarm(monotonic_time=monotonic() + seconds)
                )
                percent = round(max17.cell_percent)  # above 100% is possible!
                return max(-20, min(120, percent))
        else:
            return NO_DATA

    def batt_volts(self):
        # Check battery voltage on supported boards (unsupported: return None)
        has_max17 = (
            'adafruit_metro_esp32s3',
            'adafruit_feather_esp32s3_nopsram',
        )
        if board_id in has_max17:
            with I2C() as i2c:
                max17 = MAX17048(i2c)
                max17.wake()
                seconds = 0.5
                light_sleep_until_alarms(
                    TimeAlarm(monotonic_time=monotonic() + seconds)
                )
                return max17.cell_voltage
        else:
            return None
