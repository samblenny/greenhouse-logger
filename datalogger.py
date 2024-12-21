from alarm import sleep_memory
from digitalio import DigitalInOut
from neopixel_write import neopixel_write
from micropython import const
from rtc import RTC
from struct import pack, unpack
from time import monotonic
import time

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20


# Set this to True for additional debug prints
DEBUG = False

# For timestamping, this uses shifted and scaled unix timestamps with a
# resolution of 8 seconds. By using an epoch of 2024-12-01 instead of
# 1970-01-01, we can fit timestamps in 24 bits and the code will still work
# fine out to 2029-03-03. By using 24 bits for the timestamp and 8 bits for the
# temperature measurement, we can fit 1000 measurements in the 4096 byte
# ESP32-S3 sleep memory (allowing 96 byte header for other data).
#
# Epoch is Unix timestamp for 2024-12-01 00:00:00
#   >>> time.mktime((2024,12,1,0,0,0,0,-1,-1))
#   1733011200
EPOCH = const(1733011200)

# Pumpkin hour is the last timestamp that fits in 27 bits from epoch
#   >>> datetime.fromtimestamp(time.mktime((2024,12,1,0,0,0,0,-1,-1)) +
#   ... ((2**27)-1))
#   datetime.datetime(2029, 3, 3, 10, 42, 7)
#   >>> time.mktime((2024,12,1,0,0,0,0,-1,-1)) + ((2**27)-1)
#   1867228927
PUMPKIN_HOUR = const(1867228927)

# How many bits of timestamp to discard (3 bits means 8 second resolution)
TIME_SHIFT = const(3)

# Special value that gets recorded when there's a problem with the sensor
NO_DATA = 0x80


class SleepMem:
    # Use ESP32-S3 4096 byte sleep memory as buffer for measurements

    HEADER = const(0)
    DATA = const(96)
    END = const(HEADER + 2)
    TEMP_OOR = const(HEADER + 3)
    TIME_OOR = const(HEADER + 4)

    def __init__(self):
        if self.end == 0:
            self.end = DATA

    @property
    def end(self):
        # Getter for index of end of measurements in buffer (last is at end-1)
        return unpack('<H', sleep_memory[END:END+2])[0]

    @end.setter
    def end(self, val):
        # Setter for index of end of measurements in buffer.
        # This clips the value to fit in the range DATA..len(sleep_memory).
        clipped_val = max(DATA, min(val, len(sleep_memory)))
        sleep_memory[END:END+2] = pack('<H', clipped_val)

    @end.deleter
    def end(self):
        # Intentional NOP because deleting NV sleep memory is not meaningful
        pass

    def append_data(self, timestamp, tempF):
        # Append a measurement (24-bit time + 8-bit temperature) to buffer
        n = self.end
        # Make a note in sleep_memory if temperature is out of range
        if (tempF < -128) or (127 < tempF):
            print("WARNING: TEMPERATURE OUT OF RANGE", tempF)
            sleep_memory[TEMP_OOR] = 1
        # Make a note in sleep_memory if timestamp is out of range
        if (timestamp < EPOCH) or (PUMPKIN_HOUR < timestamp):
            print("WARNING: TIMESTAMP OUT OF RANGE", timestamp)
            sleep_memory[TIME_OOR] = 1
        # Pack timestamp as 24 bits and temp as 8 bits, save in sleep_memory.
        # To save space, this quantizes the timestamps to 8 second intervals.
        # Out of range values will be masked with & 0xFF...
        if n + 4 < len(sleep_memory):
            ts_u24 = ((timestamp - EPOCH) >> TIME_SHIFT) & 0xFFFFFF
            data_u32 = (ts_u24 << 8) | (tempF & 0xFF)
            sleep_memory[n:n+4] = pack("<I", data_u32)
            print("sleep_memory[%d] = %d" % (n, tempF))
            self.end = n + 4
        else:
            print("WARNING: BUFFER IS FULL")


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

    def record(self, tempF):
        # Save timestamped temperature measurement in ESP32 sleep memory.
        if (type(tempF) != int) or (tempF < -128) or (127 < tempF):
            tempF = NO_DATA
        self.sleepmem.append_data(time.time(), tempF)

    def measure_temp_f(self):
        # Return a temperature measurement in Fahrenheit (int8)
        if self.ds18b20:
            # .temperature is Celsius (float), so convert it
            return round((self.ds18b20.temperature * 1.8) + 32)
        return NO_DATA
