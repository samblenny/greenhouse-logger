# SPDX-License-Identifier: MIT
from board import board_id, I2C
from time import sleep

from adafruit_max1704x import MAX17048


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
    )

def battery_status():
    # Return tuple of (status source, battery volts, percent of full charge)
    source = None
    volts = None
    percent = None
    if has_max17():
        with I2C() as i2c:
            max17 = MAX17048(i2c)
            max17.wake()
            sleep(0.5)
            source = "MAX17048"
            volts = max17.cell_voltage
            percent = max17.cell_percent
    elif has_A3_divider():
        source = "A3 Divider"
    return (source, volts, percent)
