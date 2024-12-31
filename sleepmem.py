# SPDX-License-Identifier: MIT
from alarm import sleep_memory
from micropython import const
from struct import pack, unpack
import time


class SleepMem:
    # Use ESP32-S3 4096 byte sleep memory as buffer for measurements.

    HEADER = const(0)
    DATA = const(96)
    END = const(HEADER)           # length 2
    EPOCH = const(END + 2)        # length 8

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

    @property
    def epoch(self):
        # Getter for epoch timestamp (32-bit unsigned int)
        return unpack('<I', sleep_memory[EPOCH:EPOCH+4])[0]

    @epoch.setter
    def epoch(self, val):
        # Setter for epoch timestamp (32-bit unsigned int)
        sleep_memory[EPOCH:EPOCH+4] = pack('<I', val & 0xFFFFFFFF)

    def scale_centivolts(self, cV):
        # Scale a float battery voltage in centi-Volts to fit in uint8_t
        if not ((type(cV) == int) and (270 < cV < 430)):
            print("WARNING: VOLTS OUT OF RANGE", cV)
            return 0
        return cV - 270

    def unscale_centivolts(self, u8_val):
        # Invert scale_centivolts()
        return u8_val + 270

    def append_data(self, timestamp, tempF, cV):
        # Append measurements to buffer: 16-bit time, 8-bit temp, 8-bit cV
        n = self.end
        # Warn if temperature is out of range
        if not (-128 <= tempF <= 127):
            print("WARNING: TEMPERATURE OUT OF RANGE", tempF)
        # Warn if timestamp is out of range
        if (
            (timestamp < self.epoch)
            or ((timestamp - self.epoch) >> TIME_SHIFT) > 0xFFFF
            ):
            print("WARNING: TIMESTAMP OUT OF RANGE", timestamp)
        # Pack timestamp as 16 bits, temp as 8 bits, cV as 8 bits, and
        # save them in sleep_memory. To save space, this quantizes the
        # timestamps. Out of range values will be masked with & 0xFF...
        scv = self.scale_centivolts(cV)
        if n + 4 < len(sleep_memory):
            ts_u24 = ((timestamp - self.epoch) >> TIME_SHIFT) & TIME_MASK
            data_u32 = (ts_u24 << 16) | (tempF & 0xFF) << 8 | (scv & 0xFF)
            sleep_memory[n:n+4] = pack("<I", data_u32)
            print("sleep_memory[%d] = %d F, %d cV" % (n, tempF, cV))
            self.end = n + 4
        else:
            print("WARNING: BUFFER IS FULL")
