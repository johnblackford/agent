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
# File Name: coap_usp_binding.py
#
# Description: Encapsulates the various aspects of a CoAP USP Binding
#
# Class Structure:
#  - MyCoapResource(aiocoap.resource.Resource)
#    - __init__(binding, debug=False)
#    - render_get(request)
#    - render_put(request)
#    - render_delete(request)
#    - render_post(request)
#    - get_link_description()
#  - CoapReceivingThread(threading.Thread)
#    - __init__(event_loop, resource_tree, listening_port)
#    - run()
#  - CoapSendingThread(threading.Thread)
#    - __init__(serialized_msg, to_addr, debug=False)
#    - run()
#  - CoapUspBinding(generic_usp_binding.GenericUspBinding)
#    - __init__(listen_port=5683, sending_thr_timeout=5, debug=False)
#    - validate_payload(payload)
#    - send_msg(serialized_msg, to_addr)
#    - listen()
#    - clean_up()
#
"""

import logging
import threading

import asyncio
import aiocoap
import aiocoap.error
import aiocoap.resource

from agent import generic_usp_binding


try:
    from asyncio import ensure_future as asyncio_ensure_future
except ImportError:
    from asyncio import async as asyncio_ensure_future



class MyCoapResource(aiocoap.resource.Resource):
    """A CoAP Resource for receiving USP messages"""
    def __init__(self, binding, debug=False):
        """Initialize our USP CoAP Resource"""
        aiocoap.resource.Resource.__init__(self)
        self._debug = debug
        self._binding = binding
        self._logger = logging.getLogger(self.__class__.__name__)


    @asyncio.coroutine
    def render_get(self, request):
        """CoAP Resource for USP - handle the GET Method"""
        self._logger.warning("GET:: Received a CoAP Request on the USP Resource; only POST is allowed")
        return aiocoap.Message(code=aiocoap.Code.METHOD_NOT_ALLOWED)

    @asyncio.coroutine
    def render_put(self, request):
        """CoAP Resource for USP - handle the PUT Method"""
        self._logger.warning("PUT:: Received a CoAP Request on the USP Resource; only POST is allowed")
        return aiocoap.Message(code=aiocoap.Code.METHOD_NOT_ALLOWED)

    @asyncio.coroutine
    def render_delete(self, request):
        """CoAP Resource for USP - handle the DELETE Method"""
        self._logger.warning("DELETE:: Received a CoAP Request on the USP Resource; only POST is allowed")
        return aiocoap.Message(code=aiocoap.Code.METHOD_NOT_ALLOWED)

    @asyncio.coroutine
    def render_post(self, request):
        """CoAP Resource for USP - handle the POST Method"""
        self._logger.info("POST:: Received a CoAP Request on the USP Resource")
        self._logger.debug("Payload received: [%s]", request.payload)

        if request.opt.content_format == 42:
            if self._binding.validate_payload(request.payload):
                self._logger.debug("Pushing the payload of the CoAP Request onto the Binding's message queue")
                asyncio.get_event_loop().call_soon(self._binding.push, request.payload)
                response = aiocoap.Message(code=aiocoap.Code.CHANGED)
                self._logger.info("Responding to the CoAP Request with a 2.04 Status Code")
            else:
                # Failed Payload Validation, respond with 4.00
                self._logger.warning("The payload of the Incoming CoAP Request failed the Binding's validation")
                response = aiocoap.Message(code=aiocoap.Code.BAD_REQUEST)
                self._logger.info("Responding to the CoAP Request with a 4.00 Status Code")
        else:
            # Failed Content Format (expected: application/octet-stream), respond with 4.15
            self._logger.warning("Incoming CoAP Request contained an Unsupported Content-Format")
            response = aiocoap.Message(code=aiocoap.Code.UNSUPPORTED_MEDIA_TYPE)
            self._logger.info("Responding to the CoAP Request with a 4.15 Status Code")

        response.opt.content_format = 42  ### Per CoAP this is application/octet-stream

        return response

    def get_link_description(self):
        """"Configure the link description as per USP Binding Requirements"""
        link = aiocoap.resource.Resource.get_link_description(self)

        link['rt'] = "usp.endpoint"
        link['if'] = "usp.a"         # The 'if' should be "usp.c" for the USP Controller

        return link



class CoapReceivingThread(threading.Thread):
    """A Thread that executes the AsyncIO Event Loop Processing to receive CoAP messages"""
    def __init__(self, resource_tree, listening_port, debug=False):
        """Initialize the CoAP Receiving Thread"""
        threading.Thread.__init__(self, name="CoAP Receiving Thread")
        self._debug = debug
        self._resource_tree = resource_tree
        self._listening_port = listening_port
        self._logger = logging.getLogger(self.__class__.__name__)


    def run(self):
        """Listen for incoming CoAP messages for the Resources provided"""
        # The server context contains the "usp" resource, which ties back to our MyCoapResource, so when
        #  the event loop receives a message against the "usp" resource the render_XXX method in the
        #  MyCoapResource instance is called, which will push the message onto the binding (if appropriate)
        self._logger.debug("Creating a new AsyncIO Event Loop")
        my_event_loop = asyncio.new_event_loop()
        my_event_loop.set_debug(self._debug)
        asyncio.set_event_loop(my_event_loop)
        self._logger.info("Creating a CoAP Server Context for the Resource Tree")
        asyncio_ensure_future(
            aiocoap.Context.create_server_context(self._resource_tree, bind=("::", self._listening_port)))

        self._logger.info("Starting the AsyncIO CoAP Event Loop")
        my_event_loop.run_forever()
        self._logger.info("The AsyncIO CoAP Event Loop has Terminated")
        my_event_loop.close()



class CoapSendingThread(threading.Thread):
    """A Thread that executes the AsyncIO Event Loop Processing to send a single CoAP message"""
    def __init__(self, serialized_msg, to_addr, debug=False):
        """Initialize the CoAP Sending Thread"""
        threading.Thread.__init__(self, name="CoAP Sending Thread - " + to_addr)
        self._debug = debug
        self._to_addr = to_addr
        self._serialized_msg = serialized_msg
        self._logger = logging.getLogger(self.__class__.__name__)


    def run(self):
        """Send an outgoing CoAP message to the specified CoAP Address"""
        self._logger.debug("Creating a new AsyncIO Event Loop")
        my_event_loop = asyncio.new_event_loop()
        my_event_loop.set_debug(self._debug)
        asyncio.set_event_loop(my_event_loop)

        my_event_loop.run_until_complete(self._issue_request(self._to_addr, self._serialized_msg))
        my_event_loop.close()


    @asyncio.coroutine
    def _issue_request(self, to_addr, serialized_msg):
        """Send a ProtoBuf Serialized USP Message to the specified CoAP URL via the POST Method"""
        msg = aiocoap.Message(code=aiocoap.Code.POST, payload=serialized_msg)
        msg.opt.content_format = 42  ### Per CoAP this is application/octet-stream
        msg.set_request_uri(to_addr)

        self._logger.debug("Creating a CoAP Client Context")
        context = yield from aiocoap.Context.create_client_context()

        self._logger.info("Sending a CoAP message to the following address: %s", to_addr)
        self._logger.debug("Payload being sent: [%s]", serialized_msg)
        try:
            resp = yield from context.request(msg).response
            self._logger.info("CoAP Message Sent and [%s] Response received", resp.code)
        except aiocoap.error.RequestTimedOut:
            self._logger.warning("CoAP Message Sent, but no Response received due to a Timeout Error")



class CoapUspBinding(generic_usp_binding.GenericUspBinding):
    """A COAP to USP Binding"""
    def __init__(self, listen_port=5683, sending_thr_timeout=5, debug=False):
        """Initialize the CoAP USP Binding for a USP Endpoint
            - 5683 is the default CoAP port, but 5684 is the default CoAPS port"""
        generic_usp_binding.GenericUspBinding.__init__(self)
        self._debug = debug
        self._listen_thread = None
        self._listen_port = listen_port
        self._sending_thr_timeout = sending_thr_timeout
        self._resource = MyCoapResource(self, self._debug)
        self._logger = logging.getLogger(self.__class__.__name__)


    def validate_payload(self, payload):
        """Validate the payload of the Incoming CoAP message to ensure it is properly formed"""
        # TODO: Implement payload validation
        return True

    def send_msg(self, serialized_msg, to_addr):
        """Send the ProtoBuf Serialized message to the provided CoAP address"""
        self._logger.info("Starting a CoAP Sending Thread")
        coap_send_thr = CoapSendingThread(serialized_msg, to_addr, self._debug)
        coap_send_thr.start()
        coap_send_thr.join(self._sending_thr_timeout)

    def listen(self, endpoint_id):
        """Listen for incoming CoAP messages"""
        # Agent Initialization - Create a Server Resource Tree for the USP Agent
        self._logger.debug("Creating a CoAP Server Resource Tree for USP Endpoint: %s", endpoint_id)
        resource_tree = aiocoap.resource.Site()
        resource_tree.add_resource(('.well-known', 'core'),
                                   aiocoap.resource.WKCResource(resource_tree.get_resources_as_linkheader))
        resource_tree.add_resource(('usp',), self._resource)

        # An Endpoint needs a Server Context for the Resource Tree
        self._logger.info("Starting the CoAP Receiving Thread")
        self._listen_thread = CoapReceivingThread(resource_tree, self._listen_port, self._debug)
        self._listen_thread.start()

    def clean_up(self):
        """Clean up the COAP Binding - close the event loop"""
        # TODO: Maybe terminate the listening thread???
        pass
