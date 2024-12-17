<!-- SPDX-License-Identifier: MIT -->
<!-- SPDX-FileCopyrightText: Copyright 2024 Sam Blenny -->
# Greenhouse SD Logger

**WORK IN PROGRESS (ALPHA)**


## Hardware

*TODO*


### Parts

*TODO*


### Pinouts

*TODO*


### Tools and Consumables

You will need soldering tools and solder.


### Soldering the Headers

*TODO*


## Updating CircuitPython

**NOTE: To update CircuitPython on the ESP32-S3 boards, you need to use the
.BIN file (combination bootloader and CircuitPython core)**

1. Download the CircuitPython 9.2.1 **.BIN** file from the relevant page on
   circuitpython.org:
   - [Adafruit Metro ESP32-S3](https://circuitpython.org/board/adafruit_metro_esp32s3/)
   - [Adafruit QT Py ESP32-S3 4MB Flash/2MB PSRAM](https://circuitpython.org/board/adafruit_qtpy_esp32s3_4mbflash_2mbpsram/)
   - [Adafruit QT Py ESP32-S3 No PSRAM](https://circuitpython.org/board/adafruit_qtpy_esp32s3_nopsram/)

2. Follow the instructions in the
   [Web Serial ESPTool](https://learn.adafruit.com/circuitpython-with-esp32-quick-start/web-serial-esptool)
   section of the "CircuitPython on ESP32 Quick Start" learn guide to update
   your board: first erase the flash, then program the .BIN file.


## Installing CircuitPython Code

To copy the project bundle files to your CIRCUITPY drive:

1. Download the project bundle .zip file using the button on the Playground
   guide or the attachment download link on the GitHub repo Releases page.

2. Expand the zip file by opening it, or use `unzip` in a Terminal. The zip
   archive should expand to a folder. When you open the folder, it should
   contain a `README.txt` file and a `CircuitPython 9.x` folder.

3. Open the CircuitPython 9.x folder and copy all of its contents to your
   CIRCUITPY drive.

To learn more about copying libraries to your CIRCUITPY drive, check out the
[CircuitPython Libraries](https://learn.adafruit.com/welcome-to-circuitpython/circuitpython-libraries)
section of the
[Welcome to CircuitPython!](https://learn.adafruit.com/welcome-to-circuitpython)
learn guide.
