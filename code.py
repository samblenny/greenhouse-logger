# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
from board import A3
from datalogger import Datalogger, deepsleep, lightsleep
from digitalio import DigitalInOut, Direction, Pull
import time



def main():
    # This will run each time the board wakes from deep sleep.

    # Blink the LED or neopixel
    dl = Datalogger()
    dl.blink(5)

    # If A3 is jumpered to 3.3V, this light sleep loop will activate,
    # preventing deep sleeping and stopping new measurements. Light sleep
    # allows re-connecting to USB to dump measurements after running on battery
    # power with deep sleeps.
    #
    a3_3v = DigitalInOut(A3)
    a3_3v.direction = Direction.INPUT
    a3_3v.pull = Pull.DOWN
    first = True
    if a3_3v.value:
        fahrenheit = dl.measure_temp_f()
        print(fahrenheit, "°F")
        while a3_3v.value:
            lightsleep(1)
            if first:
                first = False
                print("waiting while A3 at 3.3V...")
        print("done")

    # Record a measurement
    fahrenheit = dl.measure_temp_f()
    print(fahrenheit, "°F")
    dl.record(fahrenheit)

    # Do an ESP32 deep sleep to save battery power
    deepsleep(8)
    # This doesn't return (exit to deep sleep)


main()
