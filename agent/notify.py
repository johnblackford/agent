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

# File Name: notify.py
#
# Description: Notifications for use by a USP Agent
#
# Functionality:
#   Class: Notification(object)
#    - __init__(from_endpoint_id, to_endpoint_id, subscription_id)
#    - generate_notif_msg()
#   Class: BootNotification(Notification)
#    - __init__(from_endpoint_id, to_endpoint_id, subscription_id, agent_db)
#   Class: ValueChangeNotification(Notification)
#    - __init__(from_endpoint_id, to_endpoint_id, subscription_id, param, value)
#   Class: PeriodicNotification(Notification)
#    - __init__(from_endpoint_id, to_endpoint_id, subscription_id, param)
#
"""

import logging

from agent import utils
from agent import usp_msg_pb2 as usp_msg
from agent import usp_record_pb2 as usp_record


class Notification:
    """Encapsulates a specific type of USP Notification"""
    def __init__(self, from_id, to_id, subscription_id):
        """Initialize the Notification Type"""
        self._to_id = to_id
        self._from_id = from_id
        self._subscription_id = subscription_id
        self._logger = logging.getLogger(self.__class__.__name__)

    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        raise NotImplementedError()

    def _init_notif(self, notif_msg, send_resp=False):
        """Set the Header Information of the Notification"""
        notif_msg.header.msg_id = utils.MessageIdHelper.get_message_id()
        notif_msg.header.msg_type = usp_msg.Header.NOTIFY

        notif_msg.body.request.notify.subscription_id = self._subscription_id
        notif_msg.body.request.notify.send_resp = send_resp

    def wrap_notif_in_record(self, notif_msg):
        """Wrap the Notification USP Message in a USP Record"""
        notif_record = usp_record.Record()

        notif_record.version = "1.0"
        notif_record.to_id = self._to_id
        notif_record.from_id = self._from_id
        notif_record.payload_security = usp_record.Record.PLAINTEXT
        notif_record.no_session_context.payload = notif_msg.SerializeToString()

        return notif_record


class BootNotification(Notification):
    """Encapsulates a Boot USP Notification"""
    def __init__(self, from_id, to_id, subscription_id, db):
        """Initialize the Notification Type"""
        Notification.__init__(self, from_id, to_id, subscription_id)
        self._db = db

    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        map_as_str = ""
        notif_msg = usp_msg.Msg()
        first_entry = True
        self._init_notif(notif_msg)

        # TODO: Replace hard-coded list with data model driven list
        boot_param_list = ["Device.DeviceInfo.ManufacturerOUI",
                           "Device.DeviceInfo.ProductClass",
                           "Device.DeviceInfo.SerialNumber",
                           "Device.LocalAgent.X_ARRIS-COM_IPAddr"]

        notif_msg.body.request.notify.event.obj_path = "Device.LocalAgent."
        notif_msg.body.request.notify.event.event_name = "Boot!"
        notif_msg.body.request.notify.event.params["CommandKey"] = ""
        notif_msg.body.request.notify.event.params["Cause"] = "LocalReboot"

        for path in boot_param_list:
            value = self._db.get(path)

            if first_entry:
                first_entry = False
            else:
                map_as_str += ","

            map_as_str += "\"" + path + "\""
            map_as_str += " : "
            if value is not None:
                map_as_str += "\"" + str(value) + "\""
            else:
                map_as_str += "\"\""
                self._logger.warning("Boot Param [%s] is None", path)

        notif_msg.body.request.notify.event.params["BootParameterMap"] = "{ " + map_as_str + " }"

        return notif_msg


class ValueChangeNotification(Notification):
    """Encapsulates a ValueChange USP Notification"""
    def __init__(self, from_id, to_id, subscription_id, param, value):
        """Initialize the Notification Type"""
        Notification.__init__(self, from_id, to_id, subscription_id)
        self._param = param
        self._value = value

    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        notif_msg = usp_msg.Msg()
        self._init_notif(notif_msg)

        notif_msg.body.request.notify.value_change.param_path = self._param
        notif_msg.body.request.notify.value_change.param_value = str(self._value)

        return notif_msg


class PeriodicNotification(Notification):
    """Encapsulates a Periodic USP Notification"""
    def __init__(self, from_id, to_id, subscription_id, param):
        """Initialize the Notification Type"""
        Notification.__init__(self, from_id, to_id, subscription_id)
        self._param = param

    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        notif_msg = usp_msg.Msg()
        self._init_notif(notif_msg)

        notif_msg.body.request.notify.event.obj_path = "Device.LocalAgent."
        notif_msg.body.request.notify.event.event_name = "Periodic!"

        return notif_msg
