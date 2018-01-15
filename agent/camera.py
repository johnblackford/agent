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

from agent import utils


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
        self._logger.info("Capturing picture [%s]", full_filename1)
        time.sleep(0.5)
        self._camera.capture(full_filename2)
        self._logger.info("Capturing picture [%s]", full_filename2)

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
    MAX_NUM_PICS = "Device.Services.HomeAutomation.1.Camera.1.MaxNumberOfPics"
    PIC_NUM_ENTRIES = "Device.Services.HomeAutomation.1.Camera.1.PicNumberOfEntries"

    def __init__(self, directory, filename_prefix, agent_db, port="8080"):
        RecordImage.__init__(self, directory, filename_prefix)
        self._port = port
        self._db = agent_db
        self._logger = logging.getLogger(self.__class__.__name__)


    def take_picture(self):
        param_map = {}
        agent_ip = self._db.get(self.IP_ADDR)
        max_pics = self._db.get(self.MAX_NUM_PICS)
        pic_list = RecordImage.take_picture(self)

        for pic in pic_list:
            starting_pic_num_entries = self._db.get(self.PIC_NUM_ENTRIES)
            inst_num = self._db.insert(self.PIC_TABLE)
            self._logger.info("Inserting picture instance [%s] into the DB", str(inst_num))

            # Auto-remove old instances to maintain the max table size
            if (inst_num - max_pics) > 0:
                oldest_inst_num_to_del = inst_num - max_pics
                pic_inst_num_to_del = inst_num - starting_pic_num_entries

                while pic_inst_num_to_del <= oldest_inst_num_to_del:
                    old_pic_path = self.PIC_TABLE + str(pic_inst_num_to_del) + "."
                    self._db.delete(old_pic_path)
                    self._logger.info("Removing picture instance [%s] from the DB", old_pic_path)
                    pic_inst_num_to_del += 1
                    # TODO - what about removing the file too?

            # Update the URL of the new instance
            pic_url = "http://" + agent_ip + ":" + self._port + "/camera/" + pic
            url_param_path = self.PIC_TABLE + str(inst_num) + ".URL"
            self._db.update(url_param_path, pic_url)
            self._logger.info("Updating the picture [%s] in the DB at [%s]", pic_url, url_param_path)
            param_map[url_param_path] = pic_url

        return param_map


    def _get_time_as_str(self, time_to_convert):
        timezone = self._db.get("Device.Time.LocalTimeZone")
        return utils.TimeHelper.get_time_as_str(time_to_convert, timezone)




def test():
    """Test method for the Camera"""
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                        format='%(asctime)-15s %(name)s %(levelname)-8s %(message)s')

    rec_image = RecordImage("pictures", "image")
    rec_image.take_picture()


if __name__ == "__main__":
    test()
