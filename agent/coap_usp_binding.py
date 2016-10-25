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

# File Name: coap_usp_binding.py
#
# Description: Defines a COAP USP Binding class
#
# Functionality:
#  - ListeningCoapUspBinding :: listen(), send_response(), clean_up()
#     - aiocoap.resource.Resource :: render_get(), render_post()
#  - SendingCoapUspBinding :: send_request(), clean_up()
#  - CoapMessage :: get_resp_code(), get_payload()
#
"""

import logging
import asyncio

import aiocoap
import aiocoap.resource

try:
    from asyncio import ensure_future as asyncio_ensure_future
except ImportError:
    from asyncio import async as asyncio_ensure_future



class ListeningCoapUspBinding(aiocoap.resource.Resource):
    """A USP Binding for a CoAP Agent; Used to listen for Requests and send Responses"""
    def __init__(self, port=5683, debug=False):
        """Initialize the CoAP USP Binding for a USP Endpoint
            - 5683 is the default CoAP port, but 5684 is the default CoAPS port"""
        self._port = port
        self._req_handler_callback = None

        self._resp_queue = asyncio.Queue()

        self._event_loop = asyncio.get_event_loop()
        self._event_loop.set_debug(debug)

        self._logger = logging.getLogger(self.__class__.__name__)


    @asyncio.coroutine
    def render_get(self, request):
        """COAP Resource for USP - handle the GET message"""
        self._logger.info("GET:: Received a CoAP Request on the USP Resource")
        self._logger.debug("GET:: Request payload: [%s]", request.payload)

        self._event_loop.call_soon(self._req_handler_callback, request.payload)
        self._logger.info("GET:: Starting to process incoming CoAP Request")
        coap_msg = yield from self._resp_queue.get()
        self._logger.info("GET:: Processing complete for incoming CoAP Request")
        self._logger.debug("GET:: Response payload: [%s]", coap_msg.get_payload())

        if coap_msg.get_resp_code() is None:
            resp_code = CoapMessage.RESP_CODE_GOOD_GET
        else:
            resp_code = coap_msg.get_resp_code()

        response = aiocoap.Message(code=resp_code, payload=coap_msg.get_payload())

        return response

    @asyncio.coroutine
    def render_post(self, request):
        """COAP Resource for USP - handle the POST message"""
        self._logger.info("POST:: Received a CoAP Request on the USP Resource")
        self._logger.debug("POST:: Request payload: [%s]", request.payload)

        self._event_loop.call_soon(self._req_handler_callback, request.payload)
        self._logger.info("POST:: Starting to process incoming CoAP Request")
        coap_msg = yield from self._resp_queue.get()
        self._logger.info("POST:: Processing complete for incoming CoAP Request")
        self._logger.debug("POST:: Response payload: [%s]", coap_msg.get_payload())

        if coap_msg.get_resp_code() is None:
            resp_code = CoapMessage.RESP_CODE_GOOD_POST
        else:
            resp_code = coap_msg.get_resp_code()

        response = aiocoap.Message(code=resp_code, payload=coap_msg.get_payload())

        return response

    def listen(self, callback):
        """Register the callback and run until shutdown"""
        self._req_handler_callback = callback

        # Agent Initialization - Create a Server Resource Tree for the USP Agent
        self._logger.debug("Creating a Server Resource Tree")
        resource_tree = aiocoap.resource.Site()
        resource_tree.add_resource(('.well-known', 'core'),
                                   aiocoap.resource.WKCResource(resource_tree.get_resources_as_linkheader))
        resource_tree.add_resource(('usp',), self)

        # An Agent needs a Server Context for the Resource Tree
        self._logger.info("Creating a Server Context for the Resource Tree")
        asyncio_ensure_future(
            aiocoap.Context.create_server_context(resource_tree, bind=("::", self._port)))

        self._logger.info("Starting the Event Loop")
        self._event_loop.run_forever()
        self._logger.info("Event Loop Terminated")

    def send_response(self, coap_msg):
        """Put the Response Payload on the Queue"""
        self._resp_queue.put_nowait(coap_msg)
        self._logger.debug("The response has been placed on the Queue")

    def clean_up(self):
        """Clean up the COAP Binding - close the event loop"""
        self._event_loop.close()



class SendingCoapUspBinding(object):
    """A USP Binding for a CoAP Agent; Used for Sending Notifications to a Controller"""
    def __init__(self, debug=False, new_event_loop=False):
        """Initialize the Binding and Create the COAP Client Context"""
        if new_event_loop:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._event_loop = asyncio.get_event_loop()
        self._event_loop.set_debug(debug)

        self._logger = logging.getLogger(self.__class__.__name__)


    def send_request(self, url, payload=None, callback=None):
        """Send a USP Message (Request) to the host/port specified"""
        self._event_loop.run_until_complete(self._issue_request(url, payload, callback))

    def clean_up(self):
        """Clean up the COAP Binding - close the event loop"""
        self._event_loop.close()


    @asyncio.coroutine
    def _issue_request(self, url, payload, callback):
        """Send a USP Message (Request) to the host/port specified"""
        msg = aiocoap.Message(code=aiocoap.Code.POST, payload=payload)
        msg.opt.content_format = 42         ### Per CoAP this is application/octet-stream
        msg.set_request_uri(url)

        self._logger.debug("Creating a COAP Client Context")
        context = yield from aiocoap.Context.create_client_context()
        self._logger.debug("COAP Client Context Created")

        req_future = asyncio.Future()
        if callback is not None:
            self._logger.debug("Adding a callback [%s] to this request", callback)
            req_future.add_done_callback(callback)

        self._logger.info("Using the following URI in the COAP message: %s", url)
        try:
            self._logger.info("Sending Message via COAP Binding")
            self._logger.debug("Message contents: [%s]", msg)
            resp = yield from context.request(msg).response
            self._logger.info("COAP Message Sent and Response received")
            self._logger.debug("Message contents: [%s]", resp)
        except aiocoap.error.RequestTimedOut:
            err_msg = "Request Timed Out"
            self._logger.error("Failure encountered while sending the COAP Message: %s", err_msg)
            self._logger.debug("Setting the Future's Result to the error message")
            req_future.set_result(None)
        else:
            self._logger.debug("Setting the Future's Result to the response")
            req_future.set_result(resp.payload)



class CoapMessage(object):
    """Container object for the CoAP Response Code and Payload"""
    RESP_CODE_GOOD_GET = aiocoap.Code.CONTENT
    RESP_CODE_GOOD_POST = aiocoap.Code.CHANGED
    RESP_CODE_BAD_REQ = aiocoap.Code.BAD_REQUEST
    RESP_CODE_REQ_INCOMPLETE = aiocoap.Code.REQUEST_ENTITY_INCOMPLETE
    RESP_CODE_INTERNAL_ERROR = aiocoap.Code.INTERNAL_SERVER_ERROR
    RESP_CODE_METHOD_NOT_ALLOWED = aiocoap.Code.METHOD_NOT_ALLOWED

    def __init__(self, resp_code=None, payload=""):
        """Initialize the CoAP Message"""
        self._resp_code = resp_code
        self._payload = payload


    def get_resp_code(self):
        """Retrieve the Response Code element"""
        return self._resp_code

    def get_payload(self):
        """Retrieve the payload element"""
        return self._payload
