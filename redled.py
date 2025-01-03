# SPDX-License-Identifier: MIT
import board
from digitalio import DigitalInOut
from neopixel_write import neopixel_write
from time import sleep


MORSE = {
    '^': (3, 1, 3, 1, 3),   # -.-.-  start of transmission prosign (CT, KA)
    '+': (1, 3, 1, 3, 1),   # .-.-.  end of transmission prosign
    '0': (3, 3, 3, 3, 3),   # -----
    '1': (1, 3, 3, 3, 3),   # .----
    '2': (1, 1, 3, 3, 3),   # ..---
    '3': (1, 1, 1, 3, 3),   # ...--
    '4': (1, 1, 1, 1, 3),   # ....-
    '5': (1, 1, 1, 1, 1),   # .....
    '6': (3, 1, 1, 1, 1),   # -....
    '7': (3, 3, 1, 1, 1),   # --...
    '8': (3, 3, 3, 1, 1),   # ---..
    '9': (3, 3, 3, 3, 1),   # ----.
}


class RedLED:

    def __init__(self):
        # Find a way to blink a red LED (led pin, neopixel, etc).
        #
        # This is meant to work on a few different boards:
        # - Metro S3 with LED pin (board has neopixel, but power jumper is cut)
        # - Qt Py S3 neopixel with neopixel power pin
        # - Feather S3 neopixel with neopixel power pin

        # Decide which type of LED indication to use
        b = board
        self.hasled = hasattr(b, 'LED')
        self.hasneo = hasattr(b, 'NEOPIXEL') and hasattr(b, 'NEOPIXEL_POWER')
        self.value_ = False
        self.led = self.neo = self.neopow = None
        if self.hasled:
            # First choice: Board has an LED pin
            self.led = DigitalInOut(board.LED)
            self.led.switch_to_output(value=False)
        elif self.hasneo:
            # Second choice: Board has NEOPIXEL and NEOPIXEL_POWER pins
            self.neo = DigitalInOut(board.NEOPIXEL)
            self.neopow = DigitalInOut(board.NEOPIXEL_POWER)
            self.neopow.switch_to_output(value=False)
        else:
            # Board doesn't have a useable red led option
            print("WARNING: RED LED NOT SUPPORTED ON THIS BOARD")

    def deinit(self):
        # Release CircuitPython pins
        if self.led:
            self.led.deinit()
        if self.neo:
            self.neo.deinit()
        if self.neopow:
            self.neopow.deinit()

    @property
    def value(self):
        # Get value of LED: True means on, False means off
        return self.value_

    @value.setter
    def value(self, val):
        # Set LED value: True means on, False means off
        self.value_ = val
        if self.hasled:
            # Set LED pin on or off
            self.led.value = val
        elif self.hasneo:
            # No LED pin, but board does have NEOPIXEL and NEOPIXEL_POWER pins
            if val:
                # Set neopixel on red
                grb_red = bytearray([0, 5, 0])  # red (GRB order)
                self.neopow.value = True
                sleep(0.001)  # wait 5ms for neopixel power to stabilize
                neopixel_write(self.neo, grb_red)
            else:
                # Set neopixel off
                self.neopow.value = False
        else:
            # Board doesn't have a useable red led option
            self.val_ = False
            print("WARNING: RED LED NOT SUPPORTED ON THIS BOARD")

    def morse_char(self, c):
        # Send character in morse code using the LED.
        # CAUTION: This uses a limited alphabet intended for numbers only.
        #
        # ITU-R 1677 Morse Code Timing:  3 dots per dash, 1 dot symbol gap,
        # 3 dot character gap, 7 dot word gap
        #
        # WPM Calculations, PARIS method @ 50 dots per word:
        # - dot time = (60 s) / (50 dots) / wpm = 1.20/wpm s/dot
        # - 5 WPM: 1.2/5 = 0.24 s/dot
        # - 8 WPM: 1.2/8 = 0.15 s/dot
        #
        dot = 0.17  # 7 WPM
        slp_ = sleep
        if c == ' ':
            # Gap should be 7 dots worth, but assume this comes after a
            # character that ended with a 3 dot gap. So, 3+4=7.
            self.value = False
            slp_(4 * dot)
        elif c in MORSE:
            # Loop over the dot and dash symbols of a character
            for on_dots in MORSE[c]:
                self.value = True   # on for 1 or 3 dot lengths
                slp_(on_dots * dot)
                self.value = False  # off for 1 dot length
                slp_(dot)
            # Finish the gap between characters (loop ended with 1, so 1+2=3)
            slp_(2 * dot)
