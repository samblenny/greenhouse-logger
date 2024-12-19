# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
from board import A3
from datalogger import Datalogger, deepsleep, lightsleep
from digitalio import DigitalInOut, Direction, Pull
import time



def main():
    # This will run each time the board wakes from deep sleep.

    dl = Datalogger()

    # If A3 is jumpered to GND, this light sleep loop will activate,
    # preventing deep sleeping and stopping new measurements. Light sleep
    # allows re-connecting to USB to dump measurements after running on battery
    # power with deep sleeps.
    #
    a3_gnd = DigitalInOut(A3)
    a3_gnd.direction = Direction.INPUT
    a3_gnd.pull = Pull.UP
    first = True
    if not a3_gnd.value:
        F = dl.measure_temp_f()
        print("1-wire: %d °F" % F)
        while not a3_gnd.value:
            lightsleep(1)
            if first:
                first = False
                print("waiting while A3 at GND...")
        print("done")

    # Record a measurement
    F = dl.measure_temp_f()
    print("DS18B20: %d °F" % F)
    dl.record(F)

    # Do an ESP32 deep sleep to save battery power
    deepsleep(8)
    # This doesn't return (exit to deep sleep)


main()
