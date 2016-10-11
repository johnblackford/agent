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

# File Name: coap_agent.py
#
# Description: A CoAP USP Agent
#
# Functionality:
#   Class: CoapAgent(abstract_agent.AbstractAgent)
#     __init__(dm_file, db_file, cfg_file_name="cfg/agent.json", debug=False)
#     start_listening(timeout=15)
#     clean_up()
#   Class: CoapBindingListener(threading.Thread)
#     __init__(thread_name, binding, msg_handler, timeout=15)
#     run()
#   Class: CoapPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler)
#     __init__(from_id, to_id, controller_param_path, subscription_id, param, periodic_interval)
#     add_binding(controller_param_path, binding)
#     remove_binding(controller_param_path)
#   Class: CoapValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller)
#     __init__(agent_db, poll_duration=0.5)
#     add_binding(controller_param_path, binding)
#     remove_binding(controller_param_path)
#     get_value_change_details(agent_id, controller_id, controller_param_path, subscription_id)
#   Class: CoapNotificationSender(abstract_agent.AbstractNotificationSender)
#     __init__(notif, binding, to_id)
#
"""


from agent import notify
from agent import abstract_agent
from agent import request_handler
from agent import coap_usp_binding



class CoapAgent(abstract_agent.AbstractAgent):
    """A USP Agent that uses the CoAP Binding"""
    def __init__(self, dm_file, db_file, port=5683, cfg_file_name="cfg/agent.json", debug=False):
        """Initialize the CoAP Agent"""
        abstract_agent.AbstractAgent.__init__(self, dm_file, db_file, cfg_file_name)
        self._binding = coap_usp_binding.ListeningCoapUspBinding(port, debug)

        self.set_value_change_notif_poller(CoapValueChangeNotifPoller(self._db))
        self.init_subscriptions()


    def start_listening(self):
        """Start listening for messages and process them"""
        abstract_agent.AbstractAgent.start_listening(self)

        # Listen for incoming messages
        self._binding.listen(self._handle_request)

    def clean_up(self):
        """Clean up the USP Binding"""
        self._binding.clean_up()


    def _handle_request(self, payload):
        """Handle a Request/Response interaction"""
        self._logger.info("Sending incoming Request to the Message Handler")
        try:
            req, resp, serialized_resp = self._msg_handler.handle_request(payload)
            coap_msg = coap_usp_binding.CoapMessage(payload=serialized_resp)
            abstract_agent.AbstractAgent.log_messages(self._logger, req, resp)

            # Now that we have a response, send it out
            self._binding.send_response(coap_msg)
        except request_handler.ProtocolViolationError:
            coap_msg = coap_usp_binding.CoapMessage(coap_usp_binding.CoapMessage.RESP_CODE_REQ_INCOMPLETE)
            self._logger.info("Sending a CoAP Failure as a Response")
            self._binding.send_response(coap_msg)

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        return "CoAP"

    def _get_notification_sender(self, notif, controller_id, controller_param_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        controller_host = self._db.get(controller_param_path + "CoAP.Host")
        controller_port = self._db.get(controller_param_path + "CoAP.Port")
        return CoapNotificationSender(notif, controller_host, controller_port)

    def _get_periodic_notif_handler(self, agent_id, controller_id, controller_param_path,
                                    subscription_id, param_path, periodic_interval):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        controller_host = self._db.get(controller_param_path + "CoAP.Host")
        controller_port = self._db.get(controller_param_path + "CoAP.Port")
        return CoapPeriodicNotifHandler(agent_id, controller_id, controller_param_path,
                                        subscription_id, param_path, periodic_interval,
                                        controller_host, controller_port)



class CoapPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler):
    """Issue a Periodic Notifications via a CoAP Binding"""
    def __init__(self, from_id, to_id, controller_param_path, subscription_id, param, periodic_interval,
                 controller_host, controller_port):
        """Initialize the CoAP Periodic Notification Handler"""
        abstract_agent.AbstractPeriodicNotifHandler.__init__(self, controller_param_path, from_id, to_id,
                                                             subscription_id, param, periodic_interval)
        self._controller_host = controller_host
        self._controller_port = controller_port


    def _handle_periodic(self, notif):
        """Handle the CoAP Periodic Notification"""
        notif_issuer = CoapNotificationSender(notif, self._controller_host, self._controller_port)
        notif_issuer.start()



class CoapValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller):
    """Poll Parameters for Value Change Notifications via a CoAP Binding"""
    def _handle_value_change(self, param, value, to_id, from_id, subscription_id, controller_param_path):
        """Handle the Binding Specific Value Change Processing"""
        notif = notify.ValueChangeNotification(from_id, to_id, subscription_id, param, value)

        controller_host = self._db.get(controller_param_path + "CoAP.Host")
        controller_port = self._db.get(controller_param_path + "CoAP.Port")

        self._logger.info("Sending a ValueChange Notification to %s", to_id)
        notif_issuer = CoapNotificationSender(notif, controller_host, controller_port)
        notif_issuer.start()



class CoapNotificationSender(abstract_agent.AbstractNotificationSender):
    """Send a USP Notification via a CoAP Binding"""
    def __init__(self, notif, controller_host, controller_port):
        """Initialize the CoAP Notification Sender"""
        abstract_agent.AbstractNotificationSender.__init__(self, notif)
        self._binding = None
        self._resp_payload = None
        self._controller_host = controller_host
        self._controller_port = controller_port


    def _prepare_binding(self):
        """Perform actions needed to create a binding or prepare an existing binding to send a message"""
        self._binding = coap_usp_binding.SendingCoapUspBinding(debug=True, new_event_loop=True)

    def _send_notification(self, msg):
        """Send the notification via the binding"""
        self._logger.info("Sending a Notification for Subscription ID [%s] to [%s]",
                          msg.body.request.notify.subscription_id, msg.header.to_id)
        self._binding.send_request(self._controller_host, self._controller_port,
                                   payload=msg.SerializeToString(), callback=self._handle_response)

    def _handle_response(self, resp_future):
        self._resp_payload = resp_future.result()
        self._logger.debug("CoAP Response to Notification received")

    def _clean_up_binding(self):
        """Perform actions needed to delete a binding or clean-up an existing binding that sent the message"""
        self._binding.clean_up()
