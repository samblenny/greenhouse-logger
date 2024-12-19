# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
# These are utility functions for configuring the datalogger and exporting
# logged data. This is meant to be used manually from the serial REPL.
# For example:
# >>> import util
# >>> util.set_clock()
# ...
# >>> util.reset()
# ...
# >>> util.dump()
# ...
#
from alarm import sleep_memory
from board import board_id, I2C
from rtc import RTC
from struct import unpack
from time import struct_time, sleep

from adafruit_datetime import datetime
from adafruit_max1704x import MAX17048
from datalogger import SleepMem, EPOCH, TIME_SHIFT


def batt():
    # Check battery status on supported boards
    if board_id == 'adafruit_metro_esp32s3':
        with I2C() as i2c:
            max17 = MAX17048(i2c)
            ver = max17.chip_version
            chip_id = max17.chip_id
            print("MAX17: ver=%02X, chip_id=%02X" % (ver, chip_id))
            max17.wake()
            sleep(0.5)
            volts = max17.cell_voltage
            percent = max17.cell_percent
            print("BATTERY: %.2fV, %.1f%%" % (volts, percent))
    else:
        print("Battery check for this board is not implemented yet")

def dump():
    # Print the data log in CSV format to serial console
    sm = SleepMem()
    percent = 100 * (sm.end - sm.DATA) / (len(sleep_memory) - sm.DATA)
    print("# NVRAM end index: %d (%.0f%% of buffer)" % (sm.end, percent))
    print("Date Time,Degrees F")
    for i in range(sm.DATA, sm.end, 4):
        data_u32 = unpack("<I", sleep_memory[i:i+4])[0]   # unsigned u32
        timestamp = (data_u32 >> (8 - TIME_SHIFT)) + EPOCH
        date_str = datetime.fromtimestamp(timestamp)
        tempF = unpack("<b", sleep_memory[i:i+1])[0]      # signed i8
        print('%s,%d' % (date_str, tempF))

def reset():
    ans = input("This will delete your data, are you sure? [y/N]: ")
    if ans in ["y", "Y"]:
        for i in range(len(sleep_memory)):
            sleep_memory[i] = 0
        print("SLEEP MEMORY CLEARED")

def set_clock():
    # Set the ESP32 RTC
    rtc = RTC()
    print("Current RTC time: ", now())
    print("Set RTC time...")
    try:
        y    = int(input("   year: "))
        mon  = int(input("  month: "))
        d    = int(input("    day: "))
        h    = int(input("   hour: "))
        min_ = int(input(" minute: "))
        s    = int(input("seconds: "))
        t = struct_time((y, mon, d, h, min_, s, 0, -1, -1))
        rtc.datetime = t
        print("new RTC time: ", now())
    except ValueError as e:
        print("ERROR Bad value:", e)

def now():
    # Return ESP32-S3 RTC time formatted as a string
    rtc = RTC()
    return "%04d-%02d-%02d %02d:%02d:%02d" % (rtc.datetime)[0:6]

