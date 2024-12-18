# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2024 Sam Blenny
#
from alarm import wake_alarm
from datalogger import Datalogger, deepsleep


def main():
    # This will run each time the board wakes from deep sleep.
    dl = Datalogger()
    if wake_alarm:
        # Just woke up
        dl.blink(1)
        dl.measure()
    else:
        # First boot
        dl.blink(5)
        dl.measure()
    deepsleep(8)
    # This doesn't return (exit to deep sleep)


main()
