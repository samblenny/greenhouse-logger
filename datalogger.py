# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
from alarm import (
    light_sleep_until_alarms, exit_and_deep_sleep_until_alarms, sleep_memory
)
from alarm.time import TimeAlarm
import board
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
    def __init__(self):
        # Initialize LED and 1-wire temp sensor
        qtpy_ids = (
            'adafruit_qtpy_esp32s3_nopsram',
            'adafruit_qtpy_esp32s3_4mbflash_2mbpsram',
        )
        b_id = board.board_id
        # Configure LED stuff based on the type of board
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
        # Use "A1" pin for 1-wire bus on all boards
        self.ow = OneWireBus(board.A1)
        self.ds18b20 = self.find_ds18b20(retries=3)
        # Sleep memory manager
        self.sleepmem = SleepMem()
        # Clock
        self.rtc = RTC()

    def set_clock(self):
        # Set the ESP32 RTC
        print("current time: ", end="")
        self.print_clock()
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
        except ValueError as e:
            print("ERROR Bad value:", e)

    def print_clock(self):
        # Print time from the ESP32 RTC
        t = self.rtc.datetime
        print("%04d-%02d-%02d %02d:%02d:%02d" % t[0:6])

    def blink(self, n):
        # Blink LED pin or neopixel the specified number (n) of times
        #
        # Note: CircuitPython Troubleshooting Guide lists system blink codes
        #  https://learn.adafruit.com/welcome-to-circuitpython/troubleshooting
        #  - 1 green = code finished ok
        #  - 2 red = exception
        #  - 3 yellow = safe mode
        #
        slp_ = lightsleep
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

    def onewirescan(self):
        # Scan 1-wire bus and return first DS18B20 found (family=0x28) or None
        first_temp_sensor = None
        for d in self.ow.scan():
            fam = d.family_code
            sn = d.serial_number
            suffix = ""
            if fam == 0x28:
                if (not first_temp_sensor):
                    first_temp_sensor = d
                    suffix = "(DS18B20)*"
                else:
                    suffix = "(DS18B20)"
            print(" fam:%02x, sn:%s %s" % (fam, sn.hex(), suffix))
        return first_temp_sensor

    def find_ds18b20(self, retries=3):
        # Attempt to locate DS18B20 temp sensor with retries if needed
        result = None
        for i in range(retries):
            temp_sensor = self.onewirescan()
            if temp_sensor:
                return DS18X20(self.ow, temp_sensor)
            # first try didn't work, so wait a bit before trying again
            print("RETRY", i)
            lightsleep(0.4)
        return None

    def record(self, temp_f):
        # Save temperature measurement in ESP32 sleep memory
        if not (temp_f is None):
            self.sleepmem.append_data(temp_f)

    def measure_temp_f(self):
        # Return a temperature measurement in Fahrenheit (int8)
        if not self.ds18b20:
            # Bail out if no sensor is present
            return None
        # Read Celsius (float), convert to Fahrenheit (int8)
        t_c = self.ds18b20.temperature
        t_f = round((t_c * 1.8) + 32)
        return t_f
