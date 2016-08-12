"""
Copyright (c) 2016 John Blackford

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# File Name: motion.py
#
# Description: Motion Detection Classes for RaspberryPi USP Agent
#
# Functionality:
#  - class DetectMotion(object)
#    - __init__(self, gpio_port)
#    - act_on_detected_motion(self) :: print
#  - class PersistDetectedMotion(DetectMotion)
#    - __init__(self, gpio_port, agent_db)
#    - act_on_detected_motion(self) :: write to database
#  - test() :: called from __name__ == "__main__"
#
"""


import time
import logging

import RPi.GPIO as GPIO

from agent import utils



class DetectMotion(object):
    """Base Class for handling a motion detector"""
    def __init__(self, gpio_pin):
        """Initialize the Detect Motion class"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, GPIO.PUD_DOWN)
        GPIO.add_event_detect(gpio_pin, GPIO.BOTH,
                              callback=self.act_on_detected_motion)


    def act_on_detected_motion(self, gpio_pin):
        """Print Motion Detection details"""
        if GPIO.input(gpio_pin):
            print("Motion Detected on GPIO Pin {}".format(gpio_pin))
        else:
            print("No Motion Detected on GPIO Pin {}".format(gpio_pin))



class PersistDetectedMotion(DetectMotion):
    """Persist the detection of motion to the Agent Database"""
    MIN_TRIGGER_FREQ = "Device.Services.HomeAutomation.1.Sensor.1.MinTriggerFreq"
    LAST_TRIGGER_TIME = "Device.Services.HomeAutomation.1.Sensor.1.LastTriggerTime"

    def __init__(self, gpio_pin, agent_db):
        DetectMotion.__init__(self, gpio_pin)
        self._db = agent_db
        self._logger = logging.getLogger(self.__class__.__name__)


    def act_on_detected_motion(self, gpio_pin):
        last_trigger_as_int = 0
        min_freq = self._db.get(self.MIN_TRIGGER_FREQ)
        last_trigger = self._db.get(self.LAST_TRIGGER_TIME)

        if last_trigger != "0001-01-01T00:00:00Z":
            last_trigger_substr = last_trigger[:19]
            last_trigger_as_time_struct = time.strptime(last_trigger_substr, "%Y-%m-%dT%H:%M:%S")
            last_trigger_as_int = time.mktime(last_trigger_as_time_struct)

        if GPIO.input(gpio_pin):
            now = time.time()
            if (now - last_trigger_as_int) > min_freq:
                self._logger.info("Motion Detected, updating the DB")
                self._db.update(self.LAST_TRIGGER_TIME, self._get_time_as_str(now))
            else:
                self._logger.info("Motion Detected, but too soon to update the DB")


    def _get_time_as_str(self, time_to_convert):
        timezone = self._db.get("Device.Time.LocalTimeZone")
        return utils.TimeHelper.get_time_as_str(time_to_convert, timezone)




def test():
    """Test the DetectMotion Class"""
    DetectMotion(4)
    print("Sleeping for 30 seconds")
    time.sleep(30)
    print("Exiting...")


if __name__ == "__main__":
    test()
