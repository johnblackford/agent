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

#
# File Name: stomp_agent.py
#
# Description: A STOMP USP Agent
#
# Functionality:
#   Class: StompAgent(abstract_agent.AbstractAgent)
#     __init__(dm_file, db_file, cfg_file_name="cfg/agent.json", debug=False)
#     start_listening(timeout=15)
#     clean_up()
#   Class: StompBindingListener(threading.Thread)
#     __init__(thread_name, binding, msg_handler, timeout=15)
#     run()
#   Class: StompPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler)
#     __init__(from_id, to_id, controller_param_path, subscription_id, param, periodic_interval)
#     add_binding(controller_param_path, binding)
#     remove_binding(controller_param_path)
#   Class: StompValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller)
#     __init__(agent_db, poll_duration=0.5)
#     add_binding(controller_param_path, binding)
#     remove_binding(controller_param_path)
#     get_value_change_details(agent_id, controller_id, controller_param_path, subscription_id)
#   Class: StompNotificationSender(abstract_agent.AbstractNotificationSender)
#     __init__(notif, binding, to_id)
#
"""


import logging
import threading

from agent import notify
from agent import abstract_agent
from agent import request_handler
from agent import stomp_usp_binding



class StompAgent(abstract_agent.AbstractAgent):
    """A STOMP USP Agent"""
    def __init__(self, dm_file, db_file, cfg_file_name="cfg/agent.json", debug=False):
        """Initialize the STOMP Agent"""
        abstract_agent.AbstractAgent.__init__(self, dm_file, db_file, cfg_file_name, debug)

        self._timeout = 15
        self._binding_dict = {}
        self.set_value_change_notif_poller(StompValueChangeNotifPoller(self._db))

        self._init_bindings()
        self.init_subscriptions()


    def set_listen_timeout(self, timeout):
        """Override the default 15 second listening timeout"""
        self._timeout = timeout

    def start_listening(self):
        """Start listening for messages and process them"""
        binding_listener_list = []
        abstract_agent.AbstractAgent.start_listening(self)

        # Start all of the Binding Listeners
        for binding_key in self._binding_dict:
            msg_handler = self.get_msg_handler()
            binding = self._binding_dict[binding_key]
            listener = StompBindingListener(binding_key, binding, msg_handler, self._timeout)
            listener.start()
            binding_listener_list.append(listener)

        # Wait for the Binding Listeners to complete
        for binding_listener in binding_listener_list:
            binding_listener.join()

    def clean_up(self):
        """Clean-up and prepare for shutdown"""
        for key in self._binding_dict:
            self._binding_dict[key].clean_up()


    def _init_bindings(self):
        """Initialize all Bindings from the Controller table"""
        controller_instances = self._db.find_instances("Device.Controller.")

        for instance in controller_instances:
            if self._db.get(instance + "Enable"):
                self._handle_binding(instance)
            else:
                controller_id = self._db.get(instance + "EndpointID")
                self._logger.info("Skipping disabled Controller [%s]", controller_id)

    def _handle_binding(self, controller_path):
        """Handle a Controller object"""
        protocol = self._db.get(controller_path + "Protocol")

        if protocol == self._get_supported_protocol():
            host = self._db.get(controller_path + "STOMP.Host")
            port = self._db.get(controller_path + "STOMP.Port")
            username = self._db.get(controller_path + "STOMP.Username")
            password = self._db.get(controller_path + "STOMP.Password")

            binding = stomp_usp_binding.StompUspBinding(host, port, username, password)
            binding.listen(self._endpoint_id)
            self._binding_dict[controller_path] = binding
            self.get_value_change_notif_poller().add_binding(controller_path, binding)
        else:
            self._logger.warning("Skipping controller with an invalid protocol [%s]", protocol)

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        return "STOMP"

    def _get_notification_sender(self, notif, controller_id, controller_param_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        notif_sender = None

        if controller_param_path in self._binding_dict:
            binding = self._binding_dict[controller_param_path]
            notif_sender = StompNotificationSender(notif, binding, controller_id)
        else:
            self._logger.warning("Attempted to retrieve a Notification Sender for an unknown Controller [%s]",
                                 controller_param_path)

        return notif_sender

    def _get_periodic_notif_handler(self, agent_id, controller_id, controller_param_path,
                                    subscription_id, param_path, periodic_interval):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        if controller_param_path not in self._binding_dict:
            self._logger.warning("Attempted to retrieve a Periodic Notification Handler for an unknown Controller [%s]",
                                 controller_param_path)

        periodic_notif_handler = StompPeriodicNotifHandler(agent_id, controller_id, controller_param_path,
                                                           subscription_id, param_path, periodic_interval)
        for controller_param_path in self._binding_dict:
            periodic_notif_handler.add_binding(controller_param_path,
                                               self._binding_dict[controller_param_path])

        return periodic_notif_handler



class StompBindingListener(threading.Thread):
    """Listen to a specific STOMP Binding"""
    def __init__(self, thread_name, binding, msg_handler, timeout=15):
        """Initialize the STOMP Binding Listener"""
        threading.Thread.__init__(self, name="StompBindingListener-" + thread_name)
        self._binding = binding
        self._timeout = timeout
        self._msg_handler = msg_handler
        self._logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        """Start listening for messages and process them"""
        # Listen for incoming messages
        msg_payloads = self._receive_msgs()
        for payload in msg_payloads:
            if payload is not None:
                self._handle_request(payload)


    def _receive_msgs(self):
        """Receive incoming messages from the binding"""
        try:
            while True:
                payload = self._binding.get_msg(self._timeout)
                yield payload
        except GeneratorExit:
            self._logger.info("STOMP Binding Listener is Shutting Down as requested...")

    def _handle_request(self, payload):
        """Handle a Request/Response interaction"""
        resp = None

        try:
            req, resp, serialized_resp = self._msg_handler.handle_request(payload)

            self._logger.info("Handled a [%s] Request",
                              req.body.request.WhichOneof("request"))
            self._logger.info("Sending a [%s] Response",
                              resp.body.response.WhichOneof("response"))

            # Send the message either to the "from" or "reply-to" contained in the request
            #  "reply-to" is optional and overrides the "from"
            send_to = req.header.from_id
            if len(req.header.reply_to_id) > 0:
                send_to = req.header.reply_to_id

            self._binding.send_msg(serialized_resp, send_to)

            #TODO: Check with the self._msg_handler if should shutdown, and raise a GeneratorExist
        except stomp_usp_binding.StompProtocolBindingError as err:
            self._logger.error("USP Binding Error: %s", err)
        except request_handler.ProtocolViolationError:
            # Error already logged in the USP Protocol Tool, nothing to do
            pass

        return resp



class StompPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler):
    """Issue a Periodic Notifications via a STOMP Binding"""
    def __init__(self, from_id, to_id, controller_param_path, subscription_id, param, periodic_interval):
        """Initialize the STOMP Periodic Notification Handler"""
        abstract_agent.AbstractPeriodicNotifHandler.__init__(self, controller_param_path, from_id, to_id,
                                                             subscription_id, param, periodic_interval)
        self._binding_dict = {}
        self._controller_param_path = controller_param_path


    def add_binding(self, controller_param_path, binding):
        """Add a STOMP Binding associated to a Controller Parameter Path"""
        self._binding_dict[controller_param_path] = binding

    def remove_binding(self, controller_param_path):
        """Remove a STOMP Binding"""
        del self._binding_dict[controller_param_path]


    def _handle_periodic(self, notif):
        """Handle the STOMP Periodic Notification"""
        binding_exists = True

        if self._controller_param_path in self._binding_dict:
            binding = self._binding_dict[self._controller_param_path]
            notif_issuer = StompNotificationSender(notif, binding, self._to_id)
            notif_issuer.start()
        else:
            binding_exists = False
            self._logger.warning("Could not send a Periodic Notification to an unknown Controller [%s]",
                                 self._controller_param_path)

        return binding_exists



class StompValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller):
    """Poll Parameters for Value Change Notifications via a STOMP Binding"""
    TO_ID = "to.id"
    FROM_ID = "from.id"
    CONTROLLER = "controller.path"
    SUBSCRIPTION_ID = "subscription.id"

    def __init__(self, agent_db, poll_duration=0.5):
        """Initialize the STOMP Value Change Notification Poller Thread"""
        abstract_agent.AbstractValueChangeNotifPoller.__init__(self, agent_db, poll_duration)
        self._binding_dict = {}


    def add_binding(self, controller_param_path, binding):
        """Add a STOMP Binding associated to a Controller Parameter Path"""
        self._binding_dict[controller_param_path] = binding

    def remove_binding(self, controller_param_path):
        """Remove a STOMP Binding"""
        del self._binding_dict[controller_param_path]

    def get_value_change_details(self, agent_id, controller_id, controller_param_path, subscription_id):
        """Add a STOMP Parameter to the Polling List"""
        value_change_notif_details_dict = {}

        if controller_param_path not in self._binding_dict:
            self._logger.warning("Attempted to retrieve Value Change Details for an unknown Controller [%s]",
                                 controller_param_path)

        value_change_notif_details_dict[self.FROM_ID] = agent_id
        value_change_notif_details_dict[self.TO_ID] = controller_id
        value_change_notif_details_dict[self.SUBSCRIPTION_ID] = subscription_id
        value_change_notif_details_dict[self.CONTROLLER] = controller_param_path

        return value_change_notif_details_dict


    def _handle_value_change(self, param_details_dict, param, value):
        """Handle the STOMP Value Change Processing"""
        to_id = param_details_dict[self.TO_ID]
        from_id = param_details_dict[self.FROM_ID]
        subscription_id = param_details_dict[self.SUBSCRIPTION_ID]
        controller_param_path = param_details_dict[self.CONTROLLER]
        notif = notify.ValueChangeNotification(from_id, to_id, subscription_id, param, value)

        if controller_param_path in self._binding_dict:
            binding = self._binding_dict[controller_param_path]
            self._logger.info("Sending a ValueChange Notification to %s", to_id)
            notif_issuer = StompNotificationSender(notif, binding, to_id)
            notif_issuer.start()
        else:
            self._logger.warning("Could not send ValueChange Notification to an unknown Controller [%s]",
                                 controller_param_path)



class StompNotificationSender(abstract_agent.AbstractNotificationSender):
    """Send a Notification via a STOMP Binding"""
    def __init__(self, notif, binding, to_id):
        """Initialize the STOMP Notification Issuer Thread"""
        abstract_agent.AbstractNotificationSender.__init__(self, notif)
        self._to_id = to_id
        self._binding = binding
        self._logger = logging.getLogger(self.__class__.__name__)


    def _prepare_binding(self):
        """Perform actions needed to create a binding or prepare an existing binding to send a message"""
        pass

    def _send_notification(self, msg):
        """Send the notification via the binding"""
        self._logger.info("Sending a Notification for Subscription ID [%s] to [%s]",
                          msg.body.request.notify.subscription_id, msg.header.to_id)
        self._binding.send_msg(msg.SerializeToString(), self._to_id)

    def _clean_up_binding(self):
        """Perform actions needed to delete a binding or clean-up an existing binding that sent the message"""
        pass
