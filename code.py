# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
import alarm
from alarm import (
    light_sleep_until_alarms, exit_and_deep_sleep_until_alarms
)
from alarm.pin import PinAlarm
from alarm.time import TimeAlarm
from board import A3
from datalogger import Datalogger
from digitalio import DigitalInOut, Direction, Pull
from micropython import const
from time import monotonic


# The logging interval in seconds
INTERVAL_S = const(60 * 20)

def main():
    # This will run each time the board wakes from deep sleep.

    dl = Datalogger()

    # If A3 is jumpered to GND, this light sleep loop will activate,
    # preventing deep sleeping and stopping new measurements. Light sleep
    # allows re-connecting to USB to dump measurements after running on battery
    # power with deep sleeps.
    #
    with DigitalInOut(A3) as a3_gnd:
        a3_gnd.direction = Direction.INPUT
        a3_gnd.pull = Pull.UP
        first = True
        if not a3_gnd.value:
            F = dl.measure_temp_f()
            print("1-wire: %d °F" % F)
            while not a3_gnd.value:
                seconds = 1
                light_sleep_until_alarms(
                    TimeAlarm(monotonic_time=monotonic() + seconds)
                )
                if first:
                    first = False
                    print("waiting while A3 at GND...")
            print("done")

    # Record a measurement
    F = dl.measure_temp_f()
    print("DS18B20: %d °F" % F)
    dl.record(F)

    # Do an ESP32 deep sleep to save battery power
    exit_and_deep_sleep_until_alarms(
        TimeAlarm(monotonic_time=monotonic() + INTERVAL_S),
        PinAlarm(pin=A3, value=False, pull=True)
    )
    # This doesn't return (exit to deep sleep)


main()
