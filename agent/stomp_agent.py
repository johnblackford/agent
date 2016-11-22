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
# File Name: stomp_agent.py
#
# Description: A STOMP USP Agent
#
# Functionality:
#   Class: StompAgent(abstract_agent.AbstractAgent)
#     __init__(dm_file, db_file, cfg_file_name="cfg/agent.json")
#     start_listening(timeout=15)
#     clean_up()
#   Class: StompBindingListener(threading.Thread)
#   Class: StompPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler)
#     __init__(database, mtp_param_path, from_id, to_id, subscription_id, param)
#     add_binding(controller_param_path, binding)
#     remove_binding(controller_param_path)
#   Class: StompValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller)
#     __init__(agent_db, poll_duration=0.5)
#     add_binding(mtp_param_path, binding)
#     remove_binding(mtp_param_path)
#     get_value_change_details(param, value, to_id, from_id, subscription_id, mtp_param_path)
#
"""


from agent import notify
from agent import abstract_agent
from agent import stomp_usp_binding



class StompAgent(abstract_agent.AbstractAgent):
    """A USP Agent that uses the STOMP Binding"""
    def __init__(self, dm_file, db_file, cfg_file_name="cfg/agent.json"):
        """Initialize the STOMP Agent"""
        abstract_agent.AbstractAgent.__init__(self, dm_file, db_file, cfg_file_name)
        self._binding_dict = {}

        # Initialize the underlying Agent DB MTP details for CoAP
        self._db.update("Device.LocalAgent.MTP.1.Enable", False)  # Disable the CoAP MTP
        self._db.update("Device.LocalAgent.MTP.2.Enable", True)   # Enable the STOMP MTP

        self.set_value_change_notif_poller(StompValueChangeNotifPoller(self._db))

        self._init_bindings()
        self.init_subscriptions()


    def start_listening(self, timeout=15):
        """Start listening for messages and process them"""
        binding_listener_list = []
        abstract_agent.AbstractAgent.start_listening(self)

        # Start all of the Binding Listeners
        for binding_key in self._binding_dict:
            msg_handler = self.get_msg_handler()
            binding = self._binding_dict[binding_key]
            listener = StompBindingListener(binding_key, binding, msg_handler, timeout)
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
        controller_instances = self._db.find_instances("Device.LocalAgent.Controller.")

        for controller_path in controller_instances:
            controller_id = self._db.get(controller_path + "EndpointID")

            if self._db.get(controller_path + "Enable"):
                mtp_instances = self._db.find_instances(controller_path + "MTP.")

                for mtp_path in mtp_instances:
                    if self._db.get(mtp_path + "Enable"):
                        self._handle_binding(controller_id, mtp_path)
                    else:
                        mtp_name = self._db.get(mtp_path + "Name")
                        self._logger.info("Skipping disabled MTP [%s] on Controller [%s]", mtp_name, controller_id)
            else:
                self._logger.info("Skipping disabled Controller [%s]", controller_id)

    def _handle_binding(self, controller_id, mtp_path):
        """Handle a Controller object"""
        protocol = self._db.get(mtp_path + "Protocol")

        if protocol == self._get_supported_protocol():
            host = self._db.get(mtp_path + "STOMP.Host")
            port = self._db.get(mtp_path + "STOMP.Port")
            username = self._db.get(mtp_path + "STOMP.Username")
            password = self._db.get(mtp_path + "STOMP.Password")

            binding = stomp_usp_binding.StompUspBinding(host, port, username, password)
            binding.listen(self._endpoint_id)
            self._binding_dict[mtp_path] = binding
            self.get_value_change_notif_poller().add_binding(mtp_path, binding)
        else:
            mtp_name = self._db.get(mtp_path + "Name")
            self._logger.warning("Skipping MTP [%s] on controller [%s] with an unsupported protocol [%s]",
                                 mtp_name, controller_id, protocol)

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        return "STOMP"

    def _get_notification_sender(self, notif, controller_id, mtp_param_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        notif_sender = None

        if mtp_param_path in self._binding_dict:
            to_addr = "/queue/" + controller_id
            binding = self._binding_dict[mtp_param_path]
            notif_sender = abstract_agent.NotificationSender(notif, binding, to_addr)
        else:
            self._logger.warning("Attempted to retrieve a Notification Sender for an unknown Controller/MTP [%s]",
                                 mtp_param_path)

        return notif_sender

    def _get_periodic_notif_handler(self, agent_id, controller_id, mtp_param_path,
                                    subscription_id, param_path):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        if mtp_param_path not in self._binding_dict:
            self._logger.warning(
                "Attempted to retrieve a Periodic Notification Handler for an unknown Controller/MTP [%s]",
                mtp_param_path)

        periodic_notif_handler = StompPeriodicNotifHandler(self._db, mtp_param_path, agent_id, controller_id,
                                                           subscription_id, param_path)
        for controller_param_path in self._binding_dict:
            periodic_notif_handler.add_binding(controller_param_path,
                                               self._binding_dict[controller_param_path])

        return periodic_notif_handler



class StompBindingListener(abstract_agent.BindingListener):
    """A STOMP Specific implementation of an Abstract BindingListener"""
    def _get_addr_from_id(self, to_endpoint_id):
        """STOMP Specific implementation of how to get an Endpoint Address from an Endpoint ID"""
        return "/queue/" + to_endpoint_id



class StompPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler):
    """Issue a Periodic Notifications via a STOMP Binding"""
    def __init__(self, database, mtp_param_path, from_id, to_id, subscription_id, param):
        """Initialize the STOMP Periodic Notification Handler"""
        abstract_agent.AbstractPeriodicNotifHandler.__init__(self, database, mtp_param_path,
                                                             from_id, to_id, subscription_id, param)
        self._binding_dict = {}
        self._mtp_param_path = mtp_param_path


    def add_binding(self, controller_param_path, binding):
        """Add a STOMP Binding associated to a Controller Parameter Path"""
        self._binding_dict[controller_param_path] = binding

    def remove_binding(self, controller_param_path):
        """Remove a STOMP Binding"""
        del self._binding_dict[controller_param_path]


    def _handle_periodic(self, notif):
        """Handle the STOMP Periodic Notification"""
        binding_exists = True

        if self._mtp_param_path in self._binding_dict:
            to_addr = "/queue/" + self._to_id
            msg = notif.generate_notif_msg()
            binding = self._binding_dict[self._mtp_param_path]

            self._logger.info("Sending a Periodic Notification to ID [%s] over MTP [%s] at: %s",
                              self._to_id, self._mtp_param_path, to_addr)
            binding.send_msg(msg.SerializeToString(), to_addr)
        else:
            binding_exists = False
            self._logger.warning("Could not send a Periodic Notification to an unknown Controller/MTP [%s]",
                                 self._mtp_param_path)

        return binding_exists



class StompValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller):
    """Poll Parameters for Value Change Notifications via a STOMP Binding"""
    def __init__(self, agent_db, poll_duration=0.5):
        """Initialize the STOMP Value Change Notification Poller"""
        abstract_agent.AbstractValueChangeNotifPoller.__init__(self, agent_db, poll_duration)
        self._binding_dict = {}


    def add_binding(self, mtp_param_path, binding):
        """Add a STOMP Binding associated to a Controller Parameter Path"""
        self._binding_dict[mtp_param_path] = binding

    def remove_binding(self, mtp_param_path):
        """Remove a STOMP Binding"""
        del self._binding_dict[mtp_param_path]


    def _handle_value_change(self, param, value, to_id, from_id, subscription_id, mtp_param_path):
        """Handle the STOMP Value Change Processing"""
        notif = notify.ValueChangeNotification(from_id, to_id, subscription_id, param, value)

        if mtp_param_path in self._binding_dict:
            to_addr = "/queue/" + to_id
            msg = notif.generate_notif_msg()
            binding = self._binding_dict[mtp_param_path]

            self._logger.info("Sending a ValueChange Notification to ID [%s] over MTP [%s] at: %s",
                              to_id, mtp_param_path, to_addr)
            binding.send_msg(msg.SerializeToString(), to_addr)
        else:
            self._logger.warning("Could not send ValueChange Notification to an unknown Controller/MTP [%s]",
                                 mtp_param_path)
