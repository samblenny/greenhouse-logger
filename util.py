# SPDX-License-Identifier: MIT
#
# These are utility functions for configuring the datalogger and exporting
# logged data. This is meant to be used manually from the serial REPL.
from alarm import sleep_memory
import board
from board import board_id, I2C
from rtc import RTC
from struct import unpack
import time
from time import mktime, sleep, struct_time

from adafruit_datetime import datetime
from adafruit_max1704x import MAX17048

from battery import battery_status
from redled import RedLED
from sleepmem import SleepMem


def batt():
    # Check battery status on supported boards
    (src, volts, percent) = battery_status()
    print('%s: %.2fV, %.1f%%' % (src or '--', volts or 0, percent or 0))

def dump():
    # Print the data log in CSV format to serial console
    sm = SleepMem()
    percent = 100 * (sm.end - sm.DATA) / (len(sleep_memory) - sm.DATA)
    print("# NVRAM end index: %d (%.0f%% of buffer)" % (sm.end, percent))
    print("Date Time,°F,Batt%")
    for i in range(sm.DATA, sm.end, 4):
        data_u32 = unpack("<I", sleep_memory[i:i+4])[0]   # unsigned u32
        timestamp = (data_u32 >> (16 - sm.TIME_SHIFT)) + sm.epoch
        (mon,d,h,min_,s) = datetime.fromtimestamp(timestamp).timetuple()[1:6]
        tempF = unpack("<b", sleep_memory[i+1:i+2])[0]    # signed i8
        batt =  unpack("<b", sleep_memory[i:i+1])[0]      # signed i8
        print('%d/%d %02d:%02d,%d,%d' % (mon, d, h, min_, tempF, batt))

def set_clock():
    # Clear memory, set real time clock (RTC) time, set epoch
    ans = input("This will delete your data, are you sure? [y/N]: ")
    if not (ans in ["y", "Y"]):
        print("RESET CANCELED")
        return
    # Clear sleep memory
    for i in range(len(sleep_memory)):
        sleep_memory[i] = 0
    print("SLEEP MEMORY CLEARED")
    # Set clock
    rtc = RTC()
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
    # Set epoch
    sm = SleepMem()
    sm.epoch = time.time()
    print("new epoch is: ", sm.epoch)

def now():
    # Return ESP32-S3 RTC time formatted as a string
    rtc = RTC()
    struct_ = rtc.datetime
    timestamp = mktime(struct_)
    sm = SleepMem()
    return "%04d-%02d-%02d %02d:%02d:%02d (epoch + %d)" % (
        (rtc.datetime)[0:6] + (timestamp - sm.epoch,)
    )

# Assigning the led object to a global avoids pin in use errors if you want to
# call util.discharge() more than once (testing, change your mind, etc)
_LED = None

def discharge(val):
    # Prepare battery discharge feature to activate when USB is unplugged
    sm = SleepMem()
    sm.discharge = val
    global _LED
    if not _LED:
        _LED = RedLED()
    _LED.value = val
    if val:
        print("BATTERY DISCHARGE = ARMED (begins when USB unplugged)")
    else:
        print("BATTERY DISCHARGE = DISARMED")
