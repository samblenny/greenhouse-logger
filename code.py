# SPDX-License-Identifier: MIT
import alarm
from alarm import (
    light_sleep_until_alarms, exit_and_deep_sleep_until_alarms
)
from alarm.pin import PinAlarm
from alarm.time import TimeAlarm
from board import A0, A1
from digitalio import DigitalInOut, Direction, Pull
from micropython import const
import time
from time import monotonic, sleep

from datalogger import battery_centivolts, temp_f
from sleepmem import SleepMem


# The logging interval in seconds
INTERVAL_S = const(60 * 20)

# Target discharge centi-Volts to prepare for storing the logger
STORAGE_CV = const(380)

# Low voltage threshold (centi-Volts) for power conservation features
LOW_CV = const(355)


def admin_mode(a0_gnd):
    # Admin mode pauses logging and adjusts sleep mode usage. The point is to
    # allow for USB connections (which don't work during deep sleep) and make
    # it easier to tend the batteries.

    # Putting these imports here reduces the amount of work that happens when
    # waking from deep sleep in normal logging mode. (save some battery)
    from redled import RedLED
    import gc

    # Blink logger status in morse on the LED for as long as the A0 USB-mode
    # jumper is grounded and the battery is not too low.
    led = RedLED()
    while not a0_gnd.value:
        cV = battery_centivolts()
        # Unless battery is low, send centi-Volts in Morse code on LED
        if cV and (cV > LOW_CV):
            gc.collect()
            msg = '  ^ %d %d + ' % (cV, cV)
            print(msg)
            for c in msg:
                if not a0_gnd.value:
                    led.morse_char(c)
        # Wait for a bit.
        # - When battery is above storage voltage, use time.sleep() to
        #   intentionally drain battery faster. This can be used to
        #   prepare for storing the logger.
        # - When battery is below storage voltage, use power saving
        #   light sleep (which still allows USB connections)
        if cV and (cV > STORAGE_CV):
            # Higher current draw
            led.value = True
            sleep(8)
        else:
            # Reduced current draw
            led.value = False
            light_sleep_until_alarms(
                TimeAlarm(monotonic_time=monotonic() + 15)
            )
    # Be sure LED is off
    led.value = False
    led.deinit()

def main():
    # This will run each time the board wakes from deep sleep.

    # If A0 is jumpered to GND, this admin mode loop will activate. Admin mode
    # interrupts deep sleep to allow for making a USB connection to to download
    # logs, etc.
    with DigitalInOut(A0) as a0_gnd:
        a0_gnd.direction = Direction.INPUT
        a0_gnd.pull = Pull.UP
        if not a0_gnd.value:
            admin_mode(a0_gnd)

    # Normal temperature logging mode...

    # Record a measurement
    sm = SleepMem()
    tempF = temp_f()
    cV = battery_centivolts() or 0
    print("DS18B20: %d °F, batt: %d cV" % (tempF, cV))
    sm.append_data(time.time(), tempF, cV)

    # Do an ESP32 deep sleep to save battery power
    exit_and_deep_sleep_until_alarms(
        TimeAlarm(monotonic_time=monotonic() + INTERVAL_S),
        PinAlarm(pin=A0, value=False, pull=True)
    )
    # This doesn't return (exit to deep sleep)


main()
