# Copyright (c) 2016 John Blackford
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
#
# File Name: generic_usp_binding.py
#
# Description: Defines a Generic USP Binding class that other USP Bindings
#               will be based on.
#
# Class Structure:
#  - GenericUspBinding(object)
#    - __init__(sleep_time_interval=1)
#    - push(payload)
#    - pop()
#    - get_msg(timeout=-1)
#    - not_my_msg(payload)
#    - send_msg(serialized_msg, to_addr)
#    - listen()
#    - clean_up()
#
"""


import time
import logging
import threading



class GenericUspBinding(object):
    """A Generic USP Binding class to be used by specific protocol USP Binding classes"""
    def __init__(self, sleep_time_interval=1):
        """Initialize the Generic USP Binding"""
        self._incoming_queue = []
        self._queue_lock = threading.Lock()
        self._sleep_time_interval = sleep_time_interval
        self._logger = logging.getLogger(self.__class__.__name__)


    def push(self, payload):
        """Push the provided message payload onto the end of the incoming message queue"""
        with self._queue_lock:
            self._logger.debug("Pushing a payload onto the end of the incoming message queue")
            self._incoming_queue.append(payload)

    def pop(self):
        """Pop the next payload off of the front of the incoming message queue"""
        payload = None

        with self._queue_lock:
            queue_len = len(self._incoming_queue)

            if queue_len > 0:
                self._logger.debug("Popping the next payload from the front of the incoming message queue")
                payload = self._incoming_queue.pop(0)

        return payload

    def get_msg(self, timeout=-1):
        """
          Retrieve the next incoming message from the Queue
            NOTE: timeout is measured in seconds
        """
        payload = None
        sleep_time = 0

        if timeout > 0:
            while payload is None and sleep_time < timeout:
                time.sleep(self._sleep_time_interval)
                sleep_time += self._sleep_time_interval
                payload = self.pop()
        else:
            payload = self.pop()

        return payload

    def not_my_msg(self, payload):
        """Retrieved the wrong message; Push the payload onto the end of the incoming message queue"""
        self.push(payload)

    def send_msg(self, serialized_msg, to_addr):
        """Send the ProtoBuf Serialized Message to the provided address via the Protocol-specific USP Binding"""
        raise NotImplementedError()

    def listen(self, endpoint_id):
        """Listen for incoming messages on the Protocol-specific USP Binding"""
        raise NotImplementedError()

    def clean_up(self):
        """Clean-up the Protocol-specific USP Binding after we are finished"""
        raise NotImplementedError()
