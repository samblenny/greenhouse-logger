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
from time import monotonic, sleep

from datalogger import Datalogger
from sleepmem import SleepMem


# The logging interval in seconds
INTERVAL_S = const(60 * 20)

# Target storage voltage for discharge mode
STORAGE_V = const(3.8)


def main():
    # This will run each time the board wakes from deep sleep.

    dl = Datalogger(A1)
    sm = SleepMem()

    # If A0 is jumpered to GND, this light sleep loop will activate,
    # preventing deep sleeping and stopping new measurements. Light sleep
    # allows re-connecting to USB to dump measurements after running on battery
    # power with deep sleeps.
    #
    with DigitalInOut(A0) as a0_gnd:
        a0_gnd.direction = Direction.INPUT
        a0_gnd.pull = Pull.UP
        if not a0_gnd.value:
            # Do this stuff only when USB mode jumper is connecting A0 to GND.

            # Print temperature
            F = dl.measure_temp_f()
            print("1-wire: %d °F" % F)

            # Turn on LED if battery discharge mode is armed
            from redled import RedLED
            from battery import battery_status
            import gc
            if sm.discharge:
                # DISCHARGE mode: use time.sleep() and blink voltage in morse
                print("BATTERY DISCHARGE: ACTIVE, TARGET %.2fV" % STORAGE_V)
                led = RedLED()
                # Loop until jumper is removed, using time.sleep(), instead of
                # the lower power options, to intentionally drain the battery
                (src, volts, percent) = battery_status()
                first = True
                while (not a0_gnd.value) and volts and (volts > STORAGE_V):
                    gc.collect()
                    if first:
                        first = False
                        print("waiting while A0 at GND...")
                    (src, volts, percent) = battery_status()
                    if not ((src is None) or (volts is None)):
                        print("%s: %.2fV" % (src, volts))
                        # Blink volts in Morse code on the LED
                        for c in ' ^ %.2f  %.2f + ' % (volts, volts):
                            if not a0_gnd.value:
                                led.morse_char(c)
                    # Turn LED on and wait for a bit
                    led.value = True
                    for _ in range(15):
                        if not a0_gnd.value:
                            sleep(1)
                # END OF DISCHARGE CYCLE: Be sure LED is off
                led.value = False
                led.deinit()
                # Disarm discharge mode
                sm.discharge = False
                # If jumper still installed, deep sleep until jumper removed
                if not a0_gnd.value:
                    exit_and_deep_sleep_until_alarms(
                        PinAlarm(pin=A0, value=True, pull=True)
                    )
            # Light sleep loop until jumper is removed (not discharging)
            first = True
            while not a0_gnd.value:
                if first:
                    first = False
                    print("NORMAL USB MODE (not discharging)")
                    print("waiting while A0 at GND...")
                seconds = 1
                light_sleep_until_alarms(
                    TimeAlarm(monotonic_time=monotonic() + seconds)
                )
            print("done")

    # Record a measurement
    F = dl.measure_temp_f()
    batt = dl.batt_percent()
    print("DS18B20: %d °F, batt: %d" % (F, batt))
    dl.record(F, batt)

    # Do an ESP32 deep sleep to save battery power
    exit_and_deep_sleep_until_alarms(
        TimeAlarm(monotonic_time=monotonic() + INTERVAL_S),
        PinAlarm(pin=A0, value=False, pull=True)
    )
    # This doesn't return (exit to deep sleep)


main()
