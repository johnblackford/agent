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

# File Name: utils.py
#
# Description: USP Protocol Tools for Agents
#
# Functionality:
#   Class: ConfigMgr(object)
#    - __init__(config_file_name, default_config_value_map)
#    - get_cfg_item(config_key_name)
#   Class: IPAddr(object)
#    - static: get_ip_addr(interface=None)
#   Class: UspErrMsg(object)
#    - __init__(msg_id, to_endpoint_id, from_endpoint_id, reply_to_endpoint_id=None)
#    - generate_error(error_code, error_message)
#
"""

import json
import datetime
import subprocess

from agent import usp_pb2 as usp



class ConfigMgr(object):
    """A generic Configuration Manager"""
    def __init__(self, cfg_file_name, default_cfg_val_map):
        """Initialize the ConfigMgr"""
        self._cfg_file_contents = None
        self._default_cfg_val_map = default_cfg_val_map

        try:
            with open(cfg_file_name, "r") as cfg_file:
                try:
                    self._cfg_file_contents = json.load(cfg_file)
                except ValueError:
                    self._cfg_file_contents = {}
        except FileNotFoundError:
            self._cfg_file_contents = {}


    def get_cfg_item(self, key):
        """Retrieve the Config Entry"""
        if key in self._cfg_file_contents:
            return self._cfg_file_contents[key]
        else:
            if key in self._default_cfg_val_map:
                return self._default_cfg_val_map[key]
            else:
                err_msg = "Key [{}] not found".format(key)
                raise MissingConfigError(err_msg)


class MissingConfigError(Exception):
    """A Missing Config Error"""
    pass



class UspErrMsg(object):
    """A USP Error Message object that allows a USP Agent to generate a USP Error Message
       NOTE: All generated Messages are usp_pb2.Msg format, not serialized"""
    def __init__(self, msg_id, to_id, from_id, reply_to_id=None):
        """Initialize the USP Message Header"""
        self._msg_id = msg_id
        self._to_id = to_id
        self._from_id = from_id
        self._reply_to_id = reply_to_id
        self._msg = usp.Msg()


    def _populate_header(self):
        """Populate the Header of the USP Message"""
        self._msg.header.msg_id = self._msg_id
        self._msg.header.proto_version = "1.0"
        self._msg.header.to_id = self._to_id
        self._msg.header.from_id = self._from_id

        if self._reply_to_id is not None:
            self._msg.header.reply_to_id = self._reply_to_id


    def generate_error(self, error_code, error_message):
        """Generate a USP Error Message
            NOTE: if there is no valid request, then there is no 'to' either,
               so no need to send a error back"""
        self._populate_header()
        self._msg.header.msg_type = usp.Header.ERROR
        self._msg.body.error.err_code = error_code
        self._msg.body.error.err_msg = error_message

        return self._msg



class IPAddr:
    """IP Address Retrieval Tool"""
    @staticmethod
    def get_ip_addr(intf=None):
        """Retrieve the IP Address after determining the underlying OS"""
        arg = "uname -a"
        proc = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        data = proc.communicate()
        uname_out = data[0].decode("utf-8")

        if uname_out.startswith("Darwin"):
            if intf is None:
                ip_addr = IPAddr._get_mac_ip_address()
            else:
                ip_addr = IPAddr._get_mac_ip_address(intf)
        else:
            if intf is None:
                ip_addr = IPAddr._get_rpi_ip_address()
            else:
                ip_addr = IPAddr._get_rpi_ip_address(intf)

        return ip_addr

    @staticmethod
    def _get_rpi_ip_address(netdev='eth0'):
        """Retrieve the IP Address on Raspberry Pi"""
        arg = 'ip addr show ' + netdev
        proc = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        data = proc.communicate()
        sdata = data[0].decode("utf-8").split('\n')
        ipaddr = sdata[2].strip().split(' ')[1].split('/')[0]
        return ipaddr

    @staticmethod
    def _get_mac_ip_address(netdev='en0'):
        """Retrieve the IP Address on Mac OS X"""
        arg = 'ifconfig ' + netdev
        proc = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        data = proc.communicate()
        sdata = data[0].decode("utf-8").split('\n')
        ipaddr = sdata[3].strip().split(' ')[1].split('/')[0]
        return ipaddr



class TimeHelper(object):
    """A Helper Class for getting the Time as a String"""
    @staticmethod
    def get_time_as_str(time_to_convert, timezone=None):
        """Convert the incoming Time to a String"""
        tz_part = ""

        if timezone is not None:
            tz_part = timezone.split(",")[0]

        datetime_to_convert = datetime.datetime.fromtimestamp(time_to_convert)
        datetime_as_str = datetime_to_convert.strftime("%Y-%m-%dT%H:%M:%S")

        if tz_part == "CST6CDT":
            datetime_as_str += "-06:00"
        else:
            datetime_as_str += "Z"

        return datetime_as_str
