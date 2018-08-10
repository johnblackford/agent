"""
Copyright (c) 2016-2017 John Blackford

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
import random
import datetime
import subprocess

from agent import usp_msg_pb2 as usp_msg



class ConfigMgr:
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
        value = None

        if key in self._cfg_file_contents:
            value = self._cfg_file_contents[key]
        else:
            if key in self._default_cfg_val_map:
                value = self._default_cfg_val_map[key]
            else:
                err_msg = "Key [{}] not found".format(key)
                raise MissingConfigError(err_msg)

        return value


class MissingConfigError(Exception):
    """A Missing Config Error"""
    pass



class UspErrMsg:
    """A USP Error Message object that allows a USP Agent to generate a USP Error Message
       NOTE: All generated Messages are usp_msg_pb2.Msg format, not serialized"""
    def __init__(self, msg_id):
        """Initialize the USP Message Header"""
        self._msg_id = msg_id
        self._msg = usp_msg.Msg()

    def generate_error(self, error_code, error_message):
        """Generate a USP Error Message
            NOTE: if there is no valid request, then there is no 'to' either,
               so no need to send a error back"""
        self._msg.header.msg_id = self._msg_id
        self._msg.header.msg_type = usp_msg.Header.ERROR
        self._msg.body.error.err_code = error_code
        self._msg.body.error.err_msg = error_message

        return self._msg



class MessageIdHelper:
    """A Helper class to generate Random Message IDs"""
    @staticmethod
    def get_message_id():
        """Retrieve a random message ID"""
        rand_val = random.randint(1, 10000)
        return str(rand_val)



class PathHelper:
    """A Parameter Path Helper Class"""
    @staticmethod
    def build_path_from_parts(path_parts, partial_path_part_len):
        """Build a sub-path from the provided path parts"""
        built_path = ""
        append_param = False
        built_path_part_count = 0

        if isinstance(path_parts, list):
            if partial_path_part_len >= len(path_parts):
                partial_path_part_len = len(path_parts) - 1
                append_param = True

            # We only want the path to the specified level
            if partial_path_part_len > 0:
                for part in path_parts:
                    built_path_part_count += 1
                    built_path = built_path + part + "."
                    if built_path_part_count == partial_path_part_len:
                        break

            if append_param:
                built_path += path_parts[len(path_parts) - 1]

        return built_path



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
        cmd = 'ip addr show ' + netdev
        return IPAddr._get_ipv4_address(cmd)

    @staticmethod
    def _get_mac_ip_address(netdev='en0'):
        """Retrieve the IP Address on Mac OS X"""
        cmd = 'ifconfig ' + netdev
        return IPAddr._get_ipv4_address(cmd)

    @staticmethod
    def _get_ipv4_address(command):
        """Retrieve the first IPv4 Address based on the provided RPi/MacOS command"""
        ipaddr = None
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        data = proc.communicate()
        sdata = data[0].decode("utf-8").split('\n')
        for line in sdata:
            if line.strip().startswith("inet "):
                # Retrieve an IPv4 address (ignore IPv6 addresses)
                ipaddr = line.strip().split(' ')[1].split('/')[0]
        return ipaddr



class TimeHelper:
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
