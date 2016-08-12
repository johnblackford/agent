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

# File Name: stomp_usp_binding.py
#
# Description: Defines a STOMP USP Binding class
#
# Functionality:
#   Class: StompUspBinding(stomp.ConnectionListener)
#    - on_error(headers, message) :: (stomp.ConnectionListener)
#    - on_message(headers, body) :: (stomp.ConnectionListener)
#    - listen(dest)
#    - get_msg(timeout_in_seconds=-1)
#    - re_append_msg(body)
#    - send_msg(msg, to_endpoint_id, encode_as_b64=False):
#    - clean_up()
#   Class: StompProtocolBindingError(Exception)
#
"""

import time
import logging
import threading
import base64

import stomp



class StompUspBinding(stomp.ConnectionListener):
    """A STOMP to USP Binding"""
    def __init__(self, host="127.0.0.1", port=61613, username="admin", password="admin"):
        """Initialize the Binding and Connect to the STOMP Server"""
        self._username = username
        self._password = password

        self._incoming_queue = []
        self._queue_lock = threading.Lock()

        self._logger = logging.getLogger(self.__class__.__name__)

        # If we don't use auto_decode=False, then we get decode problems
        self._conn = stomp.Connection12([(host, port)], vhost="/", auto_decode=False)
        self._conn.set_listener("defaultListener", self)
        self._conn.start()
        self._conn.connect(username, password, wait=True)


    def on_error(self, headers, message):
        """STOMP Connection Listener - handle errors"""
        self._logger.error("Received an error [%s]", message)


    def on_message(self, headers, body):
        """STOMP Connection Listener - record messages to the incoming queue"""
        stomp_body = body
        stomp_headers = headers
        self._logger.info("Message received via STOMP Binding")
        self._logger.debug("Received Message contents: [%s]", body)

        # Validate the STOMP Headers
        if "content-type" in stomp_headers:
            self._logger.debug("Validating the STOMP Headers for 'content-type'")
            if stomp_headers["content-type"].startswith("text/plain;base64"):
                self._logger.debug("STOMP Message has a proper 'content-type'")
                decoded_body = base64.b64decode(body)
                self._logger.debug("Received Message was decoded to [%s]", decoded_body)
                stomp_body = decoded_body
            elif stomp_headers["content-type"].startswith("application/octet-stream"):
                self._logger.debug("STOMP Message has a proper 'content-type'")
            else:
                self._logger.warning("STOMP Message has a bad 'content-type' [%s]",
                                     stomp_headers["content-type"])
        else:
            self._logger.warning("STOMP Message has no 'content-type'")

        # Add the STOMP Message to the queue after acquiring the lock
        with self._queue_lock:
            self._incoming_queue.append(stomp_body)


    def listen(self, dest):
        """Listen to a STOMP destination for incoming messages"""
        full_dest = self._build_dest(dest)

        #TODO: Handle the ID Better
        # Need a unique ID per destination being subscribed to
        # Need to associate a self-generated (and unique) ID to the destination
        # Need to store that destination and it's ID in a dictionary
        # Need a stop_listening(self, dest) method
        #   - Bulld the full destination: self._build_dest(dest)
        #   - Retrieve the ID from the dictionary for the destination
        #   - Unsubscribe: self._conn.unsubscribe(id)
        self._conn.subscribe(full_dest, id=1, ack="auto")


    def get_msg(self, timeout_in_seconds=-1):
        """Retrieve the incoming message from the Queue"""
        queue_len = 0
        sleep_time = 0
        sleep_time_interval = 1
        payload = None

        if timeout_in_seconds > 0:
            while payload is None and sleep_time < timeout_in_seconds:
                time.sleep(sleep_time_interval)
                sleep_time = sleep_time + sleep_time_interval

                # Acquire the Lock before accessing the queue length
                with self._queue_lock:
                    queue_len = len(self._incoming_queue)

                    if queue_len > 0:
                        self._logger.debug("Retrieving incoming message from Queue")
                        payload = self._incoming_queue.pop(0)
        else:
            # Acquire the Lock before accessing the queue length
            with self._queue_lock:
                queue_len = len(self._incoming_queue)

                if queue_len > 0:
                    self._logger.debug("Retrieving incoming message from Queue")
                    payload = self._incoming_queue.pop(0)

        return payload


    def re_append_msg(self, body):
        """Append a previous retrieved message back on the end of the queue"""
        with self._queue_lock:
            self._logger.debug("Re-Appending message to the Incoming Queue")
            self._incoming_queue.append(body)


    def send_msg(self, msg, to_addr, encode_as_b64=False):
        """Send the outgoing message to the STOMP Destination
            NOTE: the Base64 option is to get around a decoding problem
                   with stomp.py as it attempts to auto-decode the binary
                   message when using python3"""
        msg_to_send = msg
        content_type = "application/octet-stream"

        if to_addr is not None:
            if to_addr.startswith("/"):
                dest = "/queue" + to_addr
            else:
                dest = "/queue/" + to_addr

            if encode_as_b64:
                content_type = "text/plain;base64"
                msg_to_send = base64.b64encode(msg)

            self._conn.send(dest, msg_to_send, content_type)
            self._logger.info("Message sent via STOMP Binding")

            if encode_as_b64:
                self._logger.debug("Sent Message contents: [%s] encoded as [%s]",
                                   msg, msg_to_send)
            else:
                self._logger.debug("Sent Message contents: [%s]", msg_to_send)
        else:
            self.logger.error("Invalid Send Args encountered")
            raise StompProtocolBindingError("Invalid Send Args")


    def clean_up(self):
        """Clean up the STOMP Connection"""
        self._conn.disconnect()


    def _build_dest(self, dest_part):
        """Construct a proper STOMP destination from the incoming destination part"""
        dest = ""

        if dest_part.startswith("/"):
            dest = "/queue" + dest_part
        else:
            dest = "/queue/" + dest_part

        return dest



class StompProtocolBindingError(Exception):
    """A USP Protocol Binding Error"""
    pass
