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
import collections


class GenericUspBinding(object):
    """A Generic USP Binding class to be used by specific protocol USP Binding classes"""
    def __init__(self, sleep_time_interval=1):
        """Initialize the Generic USP Binding"""
        self._incoming_queue = collections.deque()
        self._sleep_time_interval = sleep_time_interval
        self._logger = logging.getLogger(self.__class__.__name__)

    def push(self, payload, reply_to_addr):
        """Push the provided message payload onto the end of the incoming message queue"""
        self._logger.debug("Pushing a Queue Item onto the end of the incoming message queue")
        self._incoming_queue.append(ExpiringQueueItem(payload, reply_to_addr))

    def pop(self):
        """Pop the next payload off of the front of the incoming message queue"""
        queue_item = None

        if len(self._incoming_queue) > 0:
            queue_item = self._incoming_queue.popleft()
            if queue_item.is_expired():
                queue_item = None
                self._logger.info("Popped an expired Queue Item, try again!")
            else:
                self._logger.debug("Popped the next Queue Item from the front of the incoming message queue")

        return queue_item

    def get_msg(self, timeout=-1):
        """
          Retrieve the next incoming Queue Item from the Queue
            NOTE: timeout is measured in seconds
        """
        queue_item = None
        sleep_time = 0

        if timeout > 0:
            while queue_item is None and sleep_time < timeout:
                time.sleep(self._sleep_time_interval)
                sleep_time += self._sleep_time_interval
                queue_item = self.pop()
        else:
            queue_item = self.pop()

        return queue_item

    def not_my_msg(self, queue_item):
        """Retrieved the wrong message; Push the payload onto the end of the incoming message queue"""
        self._logger.debug("Not my Message; Re-Pushing a Queue Item onto the end of the incoming message queue")
        self._incoming_queue.append(queue_item)

    def send_msg(self, serialized_msg, to_addr):
        """Send the ProtoBuf Serialized Message to the provided address via the Protocol-specific USP Binding"""
        raise NotImplementedError()

    def listen(self, agent_addr):
        """Listen for incoming messages on the Protocol-specific USP Binding"""
        raise NotImplementedError()

    def clean_up(self):
        """Clean-up the Protocol-specific USP Binding after we are finished"""
        raise NotImplementedError()


class ExpiringQueueItem(object):
    """A Queue Item that has a TTL and a Payload"""
    def __init__(self, payload, reply_to_addr, ttl=60):
        """Initialize the ExpiringQueueItem with the payload and a TTL (default of 60 seconds)"""
        self._ttl = ttl
        self._payload = payload
        self._create_time = time.time()
        self._reply_to_addr = reply_to_addr
        self._logger = logging.getLogger(self.__class__.__name__)

    def is_expired(self):
        """Return true if the Queue Item is older than its TTL"""
        if (self._create_time + self._ttl) < time.time():
            self._logger.warning("Expiring a Queue Item")
            return True

        return False

    def get_payload(self):
        """Retrieve the Payload"""
        return self._payload

    def get_reply_to_addr(self):
        """Retrieve the Reply to Address"""
        return self._reply_to_addr
