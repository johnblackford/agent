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


import random

from agent import usp_pb2 as usp



class Notification(object):
    """Encapsulates a specific type of USP Notification"""
    def __init__(self, from_id, to_id, subscription_id):
        """Initialize the Notification Type"""
        self._to_id = to_id
        self._from_id = from_id
        self._subscription_id = subscription_id


    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        raise NotImplementedError()

    def _init_notif(self, notif, send_resp=False):
        """Set the Header Information of the Notification"""
        notif.header.msg_id = Notification.get_message_id()
        notif.header.msg_type = usp.Header.NOTIFY
        notif.header.proto_version = "1.0"
        notif.header.to_id = self._to_id
        notif.header.from_id = self._from_id

        notif.body.request.notify.subscription_id = self._subscription_id
        notif.body.request.notify.send_resp = send_resp

    @staticmethod
    def get_message_id():
        """Retrieve a random message ID"""
        rand_val = random.randint(1, 10000)
        return str(rand_val)



class BootNotification(Notification):
    """Encapsulates a Boot USP Notification"""
    def __init__(self, from_id, to_id, subscription_id, db):
        """Initialize the Notification Type"""
        Notification.__init__(self, from_id, to_id, subscription_id)
        self._db = db


    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        notif = usp.Msg()
        self._init_notif(notif)
        boot_param_list = ["Device.LocalAgent.ManufacturerOUI",
                           "Device.LocalAgent.ProductClass",
                           "Device.LocalAgent.SerialNumber",
                           "Device.LocalAgent.X_ARRIS-COM_IPAddr"]

        notif.body.request.notify.boot.command_key = ""
        notif.body.request.notify.boot.cause = usp.Notify.Boot.LOCAL_REBOOT
        notif.body.request.notify.boot.obj_ref = "Device.LocalAgent."

        for path in boot_param_list:
            notif.body.request.notify.boot.param_map[path] = self._db.get(path)

        return notif



class ValueChangeNotification(Notification):
    """Encapsulates a ValueChange USP Notification"""
    def __init__(self, from_id, to_id, subscription_id, param, value):
        """Initialize the Notification Type"""
        Notification.__init__(self, from_id, to_id, subscription_id)
        self._param = param
        self._value = value


    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        notif = usp.Msg()
        self._init_notif(notif)

        notif.body.request.notify.value_change.param_path = self._param
        notif.body.request.notify.value_change.param_value = str(self._value)

        return notif



class PeriodicNotification(Notification):
    """Encapsulates a Periodic USP Notification"""
    def __init__(self, from_id, to_id, subscription_id, param):
        """Initialize the Notification Type"""
        Notification.__init__(self, from_id, to_id, subscription_id)
        self._param = param


    def generate_notif_msg(self):
        """Generate an appropriate USP Notification"""
        notif = usp.Msg()
        self._init_notif(notif)

        notif.body.request.notify.periodic.obj_ref = self._param

        return notif
