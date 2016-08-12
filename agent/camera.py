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

# File Name: camera.py
#
# Description: Camera Classes for RaspberryPi USP Agent
#
# Functionality:
#  - class RecordImage(object)
#    - __init__(self, directory, filename_prefix)
#    - take_picture(self) :: save to file
#  - class PersistRecordedImage(RecordImage)
#    - __init__(self, directory, filename_prefix, agent_db)
#    - take_picture(self) :: save to file and insert into database
#  - test() :: called from __name__ == "__main__"
#
"""


import time
import logging
import datetime

import picamera


LOG_FILE = "logs/agent.log"



class RecordImage(object):
    """Base Class for recording an image from the camera"""
    def __init__(self, directory, filename_prefix):
        """Initialize the Record Image class"""
        self._directory = directory
        self._filename_prefix = filename_prefix
        self._camera = picamera.PiCamera()
        self._logger = logging.getLogger(self.__class__.__name__)


    def take_picture(self):
        """Print Motion Detection details"""
        now = time.time()
        timestamp = self._get_time_as_str(now)
        filename1 = self._filename_prefix + "_" + timestamp + "_1.jpg"
        full_filename1 = self._directory + "/" + filename1
        filename2 = self._filename_prefix + "_" + timestamp + "_2.jpg"
        full_filename2 = self._directory + "/" + filename2
        self._camera.capture(full_filename1)
        self._logger.info("Capturing picture [{}]".format(full_filename1))
        time.sleep(0.5)
        self._camera.capture(full_filename2)
        self._logger.info("Capturing picture [{}]".format(full_filename2))

        return [filename1, filename2]


    def _get_time_as_str(self, time_to_convert):
        datetime_to_convert = datetime.datetime.fromtimestamp(time_to_convert)
        datetime_as_str = datetime_to_convert.strftime("%Y-%m-%dT%H:%M:%S")
        datetime_as_str += "Z"

        return datetime_as_str



class PersistRecordedImage(RecordImage):
    """Persist the recorded images to the Agent Database"""
    IP_ADDR = "Device.LocalAgent.X_ARRIS-COM_IPAddr"
    PIC_TABLE = "Device.Services.HomeAutomation.1.Camera.1.Pic."

    def __init__(self, directory, filename_prefix, agent_db, port="8080"):
        RecordImage.__init__(self, directory, filename_prefix)
        self._port = port
        self._db = agent_db
        self._logger = logging.getLogger(self.__class__.__name__)


    def take_picture(self):
        param_map = {}
        agent_ip = self._db.get(self.IP_ADDR)
        pic_list = RecordImage.take_picture(self)
        #TODO: Check number of pics in table, remove enough pics to add the list
        ### the concern here is that while we can clean up the Agent here, the
        ###  controller might have done something with those results

        for pic in pic_list:
            inst_num = self._db.insert(self.PIC_TABLE)
            pic_url = "http://" + agent_ip + ":" + self._port + "/camera/" + pic
            url_param_path = self.PIC_TABLE + str(inst_num) + ".URL"
            self._db.update(url_param_path, pic_url)
            self._logger.info("Inserting picture [{}] into the DB at [{}]"
                              .format(pic_url, url_param_path))
            param_map[url_param_path] = pic_url

        return param_map


    def _get_time_as_str(self, time_to_convert):
        tz = self._db.get("Device.Time.LocalTimeZone")
        tz_part = tz.split(",")[0]
        datetime_to_convert = datetime.datetime.fromtimestamp(time_to_convert)
        datetime_as_str = datetime_to_convert.strftime("%Y-%m-%dT%H:%M:%S")
        if tz_part == "CST6CDT":
            datetime_as_str += "-06:00"
        else:
            datetime_as_str += "Z"
        return datetime_as_str




def test():
    """Test method for the Camera"""
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                        format='%(asctime)-15s %(name)s %(levelname)-8s %(message)s')

    ri = RecordImage("pictures", "image")
    ri.take_picture()


if __name__ == "__main__":
    test()
