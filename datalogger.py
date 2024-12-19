# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
from alarm import (
    light_sleep_until_alarms, exit_and_deep_sleep_until_alarms, sleep_memory
)
from alarm.time import TimeAlarm
from board import A1, A3
from digitalio import DigitalInOut
from neopixel_write import neopixel_write
from micropython import const
from rtc import RTC
from struct import pack, unpack
from time import monotonic, struct_time

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20


def lightsleep(seconds):
    # Do an ESP32 light sleep then return
    ta = TimeAlarm(monotonic_time=monotonic() + seconds)
    light_sleep_until_alarms(ta)

def deepsleep(seconds):
    # Do an ESP32 deep sleep, which does not return (alarm triggers reboot)
    ta = TimeAlarm(monotonic_time=monotonic() + seconds)
    exit_and_deep_sleep_until_alarms(ta)


class SleepMem:
    # Use ESP32-S3 4096 byte sleep memory as buffer for measurements

    _HEADER = const(0)
    _DATA = const(96)
    _END = const(_HEADER + 2)
    _OOR = const(_HEADER + 3)

    def __init__(self):
        if self.end == 0:
            self.end = _DATA

    @property
    def end(self):
        # Getter for index of end of measurements in buffer (last is at end-1)
        return unpack('<H', sleep_memory[_END:_END+2])[0]

    @end.setter
    def end(self, val):
        # Setter for index of end of measurements in buffer
        sleep_memory[_END:_END+2] = pack('<H', val)

    @end.deleter
    def end(self):
        # Intentional NOP because deleting NV sleep memory is not meaningful
        pass

    def append_data(self, val_u8):
        # Append a measurement (8-bit unsigned int) to the buffer
        n = self.end
        if (val_u8 < 0) or (255 < val_u8):
            print("WARNING: OUT OF RANGE", val_u8)
            sleep_memory[_OOR] = 1
        if n < len(sleep_memory):
            sleep_memory[n] = val_u8 & 0xff
            print("sleep_memory[%d] = %d" % (n, sleep_memory[n]))
            self.end = n + 1
        else:
            print("WARNING: BUFFER IS FULL")

    def dump(self):
        for i in range(_DATA, self.end):
            print('%d: %3d' % (i, int(sleep_memory[i])))

    def reset(self):
        ans = input("This will delete your data, are you sure? [y/N]: ")
        if ans in ["y", "Y"]:
            for i in range(len(sleep_memory)):
                sleep_memory[i] = 0
            print("SLEEP MEMORY CLEARED")


class Datalogger:

    # Special value that gets recorded when there's a problem with the sensor
    NO_DATA = 0x80

    def __init__(self):
        # Initialize 1-wire bus, temp sensor, sleep memory, and real time clock
        self.ow = OneWireBus(A1)
        self.ds18b20 = self.find_ds18b20(retries=3)
        self.sleepmem = SleepMem()
        self.rtc = RTC()

    def set_clock(self):
        # Set the ESP32 RTC
        print("current time: ", self.rtc_str())
        print("new time...")
        try:
            y    = int(input("   year: "))
            mon  = int(input("  month: "))
            d    = int(input("    day: "))
            h    = int(input("   hour: "))
            min_ = int(input(" minute: "))
            s    = int(input("seconds: "))
            t = struct_time((y, mon, d, h, min_, s, 0, -1, -1))
            self.rtc.datetime = t
            print("new time: ", self.rtc_str())
        except ValueError as e:
            print("ERROR Bad value:", e)

    def rtc_str(self):
        # Return ESP32-S3 RTC time formatted as a string
        return "%04d-%02d-%02d %02d:%02d:%02d" % (self.rtc.datetime)[0:6]

    def find_ds18b20(self, retries=3):
        # Attempt to locate DS18B20 1-wire temp sensor with retries if needed
        print("SCANNING 1-WIRE BUS:")
        for i in range(retries):
            for d in self.ow.scan():
                fam = d.family_code
                sn = d.serial_number
                if fam == 0x28:
                    print(" fam:%02x, sn:%s" % (fam, sn.hex()))
                    return DS18X20(self.ow, d)
            # Wait a bit before retry if first attempt came up empty
            lightsleep(0.2)
        return None

    def record(self, temp_f):
        # Save temperature measurement in ESP32 sleep memory
        if not (temp_f is None):
            self.sleepmem.append_data(temp_f)

    def measure_temp_f(self):
        # Return a temperature measurement in Fahrenheit (int8)
        if self.ds18b20:
            # .temperature is Celsius (float), so convert it
            return round((self.ds18b20.temperature * 1.8) + 32)
        return NO_DATA
