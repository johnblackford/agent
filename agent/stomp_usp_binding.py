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
# File Name: stomp_usp_binding.py
#
# Description: Encapsulates the various aspects of a STOMP USP Binding
#
# Class Structure:
#  - MyStompConnListener(stomp.ConnectionListener)
#    - __init__(binding, debug=False)
#    - on_error(headers, message)
#    - on_message(headers, message)
#  - StompUspBinding(generic_usp_binding.GenericUspBinding)
#    - __init__(host="127.0.0.1", port=61613, username="admin", password="admin", debug=False)
#    - validate_payload(payload)
#    - send_msg(serialized_msg, to_addr)
#    - listen()
#    - clean_up()
#
"""

import logging

import stomp

from agent import generic_usp_binding


class MyStompConnListener(stomp.ConnectionListener):
    """A STOMP Connection Listener for receiving USP messages"""
    def __init__(self, binding, debug=False):
        """Initialize our STOMP Connection Listener"""
        stomp.ConnectionListener.__init__(self)
        self._debug = debug
        self._binding = binding
        self._subscribe_dest = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def get_subscribe_dest(self):
        """Retreive the current value of the internal subscribe_dest value"""
        return self._subscribe_dest

    def on_error(self, headers, message):
        """STOMP Connection Listener - handle errors"""
        self._logger.error("Received an error [%s]", message)

    def on_connected(self, headers, body):
        """STOMP Connection Listener - received CONNECTED frame; look for subscribe-dest header"""
        if "subscribe-dest" in headers:
            self._subscribe_dest = headers["subscribe-dest"]
            self._logger.info("Found 'subscribe-dest' in the headers of the CONNECTED frame with a value of: %s",
                              self._subscribe_dest)
        else:
            self._logger.debug("The 'subscribe-dest' header was NOT found in the CONNECTED frame")

    def on_message(self, headers, body):
        """STOMP Connection Listener - record messages to the incoming queue"""
        self._logger.info("Received a STOMP message on my USP Message Queue")
        self._logger.debug("Payload received: [%s]", body)

        # Validate the STOMP Headers
        if "content-type" in headers:
            self._logger.debug("Validating the STOMP Headers for 'content-type'")

            if headers["content-type"].startswith("application/vnd.bbf.usp.msg"):
                self._logger.debug("STOMP Message has a proper 'content-type'")

                if "reply-to-dest" in headers:
                    self._logger.debug("STOMP Message has a 'reply-to-dest'")
                    self._binding.push(body, headers["reply-to-dest"])
                else:
                    self._logger.warning("Incoming STOMP message had no 'reply-to-dest' header")
            else:
                self._logger.warning("Incoming STOMP message contained an Unsupported Content-Type: %s",
                                     headers["content-type"])
        else:
            self._logger.warning("Incoming STOMP message had no Content-Type")


class StompUspBinding(generic_usp_binding.GenericUspBinding):
    """A STOMP to USP Binding"""
    def __init__(self, my_endpoint_id, host="127.0.0.1", port=61613, username="admin", password="admin",
                 virtual_host="/", outgoing_heartbeats=0, incoming_heartbeats=0, debug=False):
        """Initialize the STOMP USP Binding for a USP Endpoint
            - 61613 is the default STOMP port for RabbitMQ installations"""
        generic_usp_binding.GenericUspBinding.__init__(self)
        self._host = host
        self._port = port
        self._debug = debug
        self._my_dest = None
        self._username = username
        self._password = password
        self._my_endpoint_id = my_endpoint_id
        self._listener = MyStompConnListener(self, debug)
        self._logger = logging.getLogger(self.__class__.__name__)

        # If we don't use auto_decode=False, then we get decode problems
        self._conn = stomp.Connection12([(host, port)], heartbeats=(outgoing_heartbeats, incoming_heartbeats),
                                        vhost=virtual_host, auto_decode=False)
        self._conn.set_listener("defaultListener", self._listener)
        self._conn.start()
        self._conn.connect(username, password, wait=True, headers={"endpoint-id": self._my_endpoint_id})

    def send_msg(self, serialized_msg, to_addr):
        """Send the ProtoBuf Serialized message to the provided STOMP address"""
        content_type = "application/vnd.bbf.usp.msg"
        usp_headers = {"reply-to-dest": self._my_dest}
        self._logger.debug("Using [%s] as the value of the reply-to-dest header", self._my_dest)
        self._conn.send(to_addr, serialized_msg, content_type, usp_headers)
        self._logger.info("Sending a STOMP message to the following address: %s", to_addr)
        self._logger.debug("Payload being sent: [%s]", serialized_msg)

    def listen(self, agent_addr):
        """Listen to a STOMP destination for incoming messages"""
        msg_id = 1

        self._my_dest = self._listener.get_subscribe_dest()
        if self._my_dest is None:
            self._my_dest = agent_addr
            self._logger.info("Using Destination [%s] as retrieved from the data model", self._my_dest)
        else:
            self._logger.info("Using Destination [%s] as discovered in the CONNECTED frame headers", self._my_dest)

        # TODO: Handle the ID Better
        # Need a unique ID per destination being subscribed to
        # Need to associate a self-generated (and unique) ID to the destination
        # Need to store that destination and it's ID in a dictionary
        # Need a stop_listening(self, dest) method
        #   - Bulld the full destination: self._build_dest(dest)
        #   - Retrieve the ID from the dictionary for the destination
        #   - Unsubscribe: self._conn.unsubscribe(id)
        self._conn.subscribe(agent_addr, id=str(msg_id), ack="auto")
        self._logger.info("Subscribed to Destination: %s", agent_addr)

    def clean_up(self):
        """Clean up the STOMP Connection"""
        self._conn.disconnect()
