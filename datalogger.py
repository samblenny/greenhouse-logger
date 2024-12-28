# SPDX-License-Identifier: MIT
from alarm import sleep_memory, light_sleep_until_alarms
from alarm.time import TimeAlarm
from board import board_id, I2C
from digitalio import DigitalInOut
from neopixel_write import neopixel_write
from micropython import const
from rtc import RTC
from struct import pack, unpack
from time import monotonic
import time

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from adafruit_max1704x import MAX17048


# Set this to True for additional debug prints
DEBUG = False

# Special value that gets recorded when there's a problem with the sensor
NO_DATA = 0x80


class SleepMem:
    # Use ESP32-S3 4096 byte sleep memory as buffer for measurements.

    HEADER = const(0)
    DATA = const(96)
    END = const(HEADER)        # length 2
    EPOCH = const(HEADER + 2)  # length 8

    TIME_SHIFT = const(5)      # quantize times to 32 seconds
    TIME_MASK = const(0xFFFF)  # max time is ((2**16-1)<<5)/60/60/24 = 24 days

    def __init__(self):
        # Set some non-terrible defaults on first boot or after a hard reset
        if self.end == 0:
            self.end = DATA
        if self.epoch == 0:
            self.epoch = time.time()

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

#     @end.deleter
#     def end(self):
#         # Intentional NOP because deleting NV sleep memory is not meaningful
#         pass

    @property
    def epoch(self):
        # Getter for epoch timestamp (32-bit unsigned int)
        return unpack('<I', sleep_memory[EPOCH:EPOCH+4])[0]

    @epoch.setter
    def epoch(self, val):
        # Setter for epoch timestamp (32-bit unsigned int)
        sleep_memory[EPOCH:EPOCH+4] = pack('<I', val & 0xFFFFFFFF)

#     @epoch.deleter
#     def epoch(self):
#         # Intentional NOP because deleting NV sleep memory is not meaningful
#         pass

    def append_data(self, timestamp, tempF, batt):
        # Append measurements to buffer: 16-bit time, 8-bit temp, 8-bit battery
        n = self.end
        # Warn if temperature is out of range
        if (tempF < -128) or (127 < tempF):
            print("WARNING: TEMPERATURE OUT OF RANGE", tempF)
        # Warn if timestamp is out of range
        if (
            (timestamp < self.epoch)
            or ((timestamp - self.epoch) >> TIME_SHIFT) > 0xFFFF
            ):
            print("WARNING: TIMESTAMP OUT OF RANGE", timestamp)
        # Pack timestamp as 16 bits, temp as 8 bits, battery as 8 bits, and
        # save them in sleep_memory. To save space, this quantizes the
        # timestamps. Out of range values will be masked with & 0xFF...
        if n + 4 < len(sleep_memory):
            ts_u24 = ((timestamp - self.epoch) >> TIME_SHIFT) & TIME_MASK
            data_u32 = (ts_u24 << 16) | (tempF & 0xFF) << 8 | (batt & 0xFF)
            sleep_memory[n:n+4] = pack("<I", data_u32)
            print("sleep_memory[%d] = %d F, %d%%" % (n, tempF, batt))
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

