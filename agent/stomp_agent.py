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


import time

from agent import utils
from agent import notify
from agent import abstract_agent
from agent import stomp_usp_binding



class StompAgent(abstract_agent.AbstractAgent):
    """A USP Agent that uses the STOMP Binding"""
    def __init__(self, dm_file, db_file, net_intf, cfg_file_name="cfg/agent.json", debug=False):
        """Initialize the STOMP Agent"""
        abstract_agent.AbstractAgent.__init__(self, dm_file, db_file, net_intf, cfg_file_name, debug)
        self._binding_dict = {}

        # Format: { StompConnRef : { ControllerID : StompDestination } }
        self._controller_stomp_conn_ref_dict = {}

        self.set_value_change_notif_poller(StompValueChangeNotifPoller(self._db))

        self._init_db_for_mtp()
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
            controller_dest_dict = self._controller_stomp_conn_ref_dict[binding_key]
            listener = StompBindingListener(binding_key, binding, msg_handler, controller_dest_dict, timeout)
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
        self._build_ctrl_stomp_conn_dict()
        agent_stomp_conn_dict = self._get_agent_stomp_conns()

        for agent_stomp_conn in agent_stomp_conn_dict:
            agent_dest = agent_stomp_conn_dict[agent_stomp_conn]
            self._create_binding(agent_stomp_conn, agent_dest)

    def _build_ctrl_stomp_conn_dict(self):
        """Build out the STOMP Connection dictionary for the known Controllers"""
        controller_instances = self._db.find_instances("Device.LocalAgent.Controller.")

        for controller_path in controller_instances:
            controller_id = self._db.get(controller_path + "EndpointID")

            if self._db.get(controller_path + "Enable"):
                self._find_valid_controller_mtps(controller_id, controller_path)
            else:
                self._logger.info("Skipping disabled Controller [%s]", controller_id)

    def _find_valid_controller_mtps(self, controller_id, controller_path):
        """Validate the STOMP Connections for the MTPs associated with the provided Controller
            -- Build out the _controller_stomp_conn_ref_dict
        """
        controller_stomp_dest = None
        mtp_instances = self._db.find_instances(controller_path + "MTP.")

        for mtp_path in mtp_instances:
            mtp_alias = self._db.get(mtp_path + "Alias")

            if self._db.get(mtp_path + "Enable"):
                protocol = self._db.get(mtp_path + "Protocol")

                if protocol == self._get_supported_protocol():
                    if controller_stomp_dest is None:
                        controller_stomp_dest = self._db.get(mtp_path + "STOMP.Destination")
                        controller_stomp_conn = self._db.get(mtp_path + "STOMP.Reference") + "."

                        if controller_stomp_conn not in self._controller_stomp_conn_ref_dict:
                            self._controller_stomp_conn_ref_dict[controller_stomp_conn] = {}

                        self._logger.info("Found STOMP Controller [%s] on Server [%s] and Destination [%s]",
                                          controller_id, controller_stomp_conn, controller_stomp_dest)
                        self._controller_stomp_conn_ref_dict[controller_stomp_conn][controller_id] = \
                            controller_stomp_dest
                    else:
                        self._logger.warning(
                            "Skipping MTP [%s] on controller [%s] - STOMP Destination already found",
                            mtp_alias, controller_id
                        )
                else:
                    self._logger.warning(
                        "Skipping MTP [%s] on controller [%s] with an unsupported protocol [%s]",
                        mtp_alias, controller_id, protocol)
            else:
                self._logger.warning("Skipping disabled MTP [%s] on Controller [%s]", mtp_alias, controller_id)

    def _get_agent_stomp_conns(self):
        """Retrieve the STOMP Connections associated with the Agent that are also associated by a known Controller"""
        agent_stomp_conn_dict = {}
        agent_mtp_instances = self._db.find_instances("Device.LocalAgent.MTP.")

        for agent_mtp_path in agent_mtp_instances:
            mtp_alias = self._db.get(agent_mtp_path + "Alias")

            if self._db.get(agent_mtp_path + "Enable"):
                protocol = self._db.get(agent_mtp_path + "Protocol")

                if protocol == self._get_supported_protocol():
                    agent_dest = self._db.get(agent_mtp_path + "STOMP.Destination")
                    agent_stomp_conn = self._db.get(agent_mtp_path + "STOMP.Reference") + "."

                    if self._db.get(agent_stomp_conn + "Enable"):
                        if agent_stomp_conn in self._controller_stomp_conn_ref_dict:
                            self._logger.info("Found STOMP MTP on Server [%s] and Destination [%s]",
                                              agent_stomp_conn, agent_dest)
                            agent_stomp_conn_dict[agent_stomp_conn] = agent_dest
                        else:
                            self._logger.warning("Skipping Agent's MTP [%s], no associated Controller", mtp_alias)
                    else:
                        self._logger.warning("Skipping Agent's MTP [%s], associated STOMP Connection is disabled",
                                             mtp_alias)
                else:
                    self._logger.warning("Skipping Agent's MTP [%s] with an unsupported protocol [%s]",
                                         mtp_alias, protocol)
            else:
                self._logger.warning("Skipping Agent's disabled MTP [%s]", mtp_alias)

        return agent_stomp_conn_dict


    def _create_binding(self, stomp_conn_ref, listen_dest):
        """Create a STOMP Binding object"""
        incoming_heartbeats = 0
        outgoing_heartbeats = 0
        host = self._db.get(stomp_conn_ref + "Host")
        port = self._db.get(stomp_conn_ref + "Port")
        username = self._db.get(stomp_conn_ref + "Username")
        password = self._db.get(stomp_conn_ref + "Password")
        virtual_host = self._db.get(stomp_conn_ref + "VirtualHost")
        timezone = self._db.get("Device.Time.LocalTimeZone")

        if self._db.get(stomp_conn_ref + "EnableHeartbeats"):
            outgoing_heartbeats = self._db.get(stomp_conn_ref + "OutgoingHeartbeat")
            incoming_heartbeats = self._db.get(stomp_conn_ref + "IncomingHeartbeat")

        # Set the STOMP Connection Status to Connecting
        self._db.update(stomp_conn_ref + "Status", "Connecting")
        self._db.update(stomp_conn_ref + "LastChangeDate", utils.TimeHelper.get_time_as_str(time.time(), timezone))
        self._logger.info("Connecting to %s", stomp_conn_ref)

        binding = stomp_usp_binding.StompUspBinding(host, port, username, password, virtual_host,
                                                    outgoing_heartbeats, incoming_heartbeats)

        # Set the STOMP Connection Status to Enabled
        self._db.update(stomp_conn_ref + "Status", "Enabled")
        self._db.update(stomp_conn_ref + "LastChangeDate", utils.TimeHelper.get_time_as_str(time.time(), timezone))
        self._logger.info("Connected to %s", stomp_conn_ref)

        # Start listening
        binding.listen(self._endpoint_id, listen_dest)

        # Save the binding, and configure the ValueChangeNotifPoller
        self._binding_dict[stomp_conn_ref] = binding

        # Update the ValueChangeNotifPoller for the Binding and Controller Destinations
        self.get_value_change_notif_poller().add_binding(stomp_conn_ref, binding)
        for controller_endpoint_id in self._controller_stomp_conn_ref_dict[stomp_conn_ref]:
            self.get_value_change_notif_poller().add_controller_dest(
                controller_endpoint_id, self._controller_stomp_conn_ref_dict[stomp_conn_ref][controller_endpoint_id])

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        return "STOMP"

    def _init_db_for_mtp(self):
        """Enable the LocalAgent MTPs for the supported protocol and Disable all other LocalAgent MTPs"""
        agent_mtp_instances = self._db.find_instances("Device.LocalAgent.MTP.")

        for agent_mtp_path in agent_mtp_instances:
            if self._db.get(agent_mtp_path + "Protocol") == self._get_supported_protocol():
                self._db.update(agent_mtp_path + "Enable", True)
            else:
                self._db.update(agent_mtp_path + "Enable", False)

    def _get_notification_sender(self, notif, controller_id, mtp_param_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        notif_sender = None
        controller_stomp_conn = self._db.get(mtp_param_path + "STOMP.Reference") + "."

        if controller_stomp_conn in self._binding_dict:
            to_addr = "/queue/" + controller_id
            binding = self._binding_dict[controller_stomp_conn]
            notif_sender = abstract_agent.NotificationSender(notif, binding, to_addr)
        else:
            self._logger.warning("Attempted to retrieve a Notification Sender for an unknown Controller/MTP [%s]",
                                 mtp_param_path)

        return notif_sender

    def _get_periodic_notif_handler(self, agent_id, controller_id, mtp_param_path,
                                    subscription_id, param_path):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        periodic_notif_handler = None
        controller_stomp_conn = self._db.get(mtp_param_path + "STOMP.Reference") + "."

        if controller_stomp_conn in self._binding_dict:
            controller_dest_dict = self._controller_stomp_conn_ref_dict[controller_stomp_conn]
            periodic_notif_handler = StompPeriodicNotifHandler(self._db, mtp_param_path, agent_id, controller_id,
                                                               subscription_id, param_path, controller_dest_dict)

            periodic_notif_handler.set_binding(self._binding_dict[controller_stomp_conn])
        else:
            self._logger.warning(
                "Attempted to retrieve a Periodic Notification Handler for an unknown Controller/MTP [%s]",
                mtp_param_path)

        return periodic_notif_handler



class StompBindingListener(abstract_agent.BindingListener):
    """A STOMP Specific implementation of an Abstract BindingListener"""
    def __init__(self, thread_name, binding, msg_handler, controller_dest_dict, timeout=15):
        """Initialize the STOMP Binding Listener"""
        abstract_agent.BindingListener.__init__(self, thread_name, binding, msg_handler, timeout)

        self._controller_dest_dict = controller_dest_dict


    def _get_addr_from_id(self, to_endpoint_id):
        """STOMP Specific implementation of how to get an Endpoint Address from an Endpoint ID"""
        to_addr = None

        if to_endpoint_id in self._controller_dest_dict:
            to_addr = self._controller_dest_dict[to_endpoint_id]
            self._logger.info("Using Address [%s] for Controller [%s]", to_addr, to_endpoint_id)

        return to_addr



class StompPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler):
    """Issue a Periodic Notifications via a STOMP Binding"""
    def __init__(self, database, mtp_param_path, from_id, to_id, subscription_id,
                 path_to_periodic_params, controller_dest_dict):
        """Initialize the STOMP Periodic Notification Handler"""
        abstract_agent.AbstractPeriodicNotifHandler.__init__(self, database, mtp_param_path,
                                                             from_id, to_id, subscription_id,
                                                             path_to_periodic_params)
        self._mtp_param_path = mtp_param_path
        self._controller_dest_dict = controller_dest_dict


    def _handle_periodic(self, notif):
        """Handle the STOMP Periodic Notification"""
        binding_exists = True

        if self._binding is not None:
            # Ensure the Controller Endpoint ID is known
            if self._to_id in self._controller_dest_dict:
                to_addr = self._controller_dest_dict[self._to_id]
                msg = notif.generate_notif_msg()

                self._logger.info("Sending a Periodic Notification to ID [%s] over MTP [%s] at: %s",
                                  self._to_id, self._mtp_param_path, to_addr)
                self._binding.send_msg(msg.SerializeToString(), to_addr)
            else:
                self._logger.warning("Could not send a Periodic Notification to an unknown Controller [%s]",
                                     self._to_id)
        else:
            binding_exists = False
            self._logger.warning("Could not send a Periodic Notification to Controller/MTP [%s] - No Binding",
                                 self._mtp_param_path)

        return binding_exists



class StompValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller):
    """Poll Parameters for Value Change Notifications via a STOMP Binding"""
    def __init__(self, agent_db, poll_duration=0.5):
        """Initialize the STOMP Value Change Notification Poller"""
        abstract_agent.AbstractValueChangeNotifPoller.__init__(self, agent_db, poll_duration)
        self._binding_dict = {}
        self._controller_dest_dict = {}


    def add_binding(self, stomp_conn_ref, binding):
        """Add a STOMP Binding associated to a Controller Parameter Path"""
        self._binding_dict[stomp_conn_ref] = binding

    def remove_binding(self, stomp_conn_ref):
        """Remove a STOMP Binding"""
        del self._binding_dict[stomp_conn_ref]


    def add_controller_dest(self, controller_endpoint_id, dest_list):
        """Add a STOMP Binding associated to a Controller Parameter Path"""
        self._controller_dest_dict[controller_endpoint_id] = dest_list

    def remove_controller_dest(self, controller_endpoint_id):
        """Remove a STOMP Binding"""
        del self._controller_dest_dict[controller_endpoint_id]


    def _handle_value_change(self, param, value, to_id, from_id, subscription_id, mtp_param_path):
        """Handle the STOMP Value Change Processing"""
        controller_stomp_conn = self._db.get(mtp_param_path + "STOMP.Reference") + "."
        notif = notify.ValueChangeNotification(from_id, to_id, subscription_id, param, value)

        if controller_stomp_conn in self._binding_dict:
            # Ensure the Controller Endpoint ID is known
            if to_id in self._controller_dest_dict:
                to_addr = self._controller_dest_dict[to_id]
                msg = notif.generate_notif_msg()
                binding = self._binding_dict[controller_stomp_conn]

                self._logger.info("Sending a ValueChange Notification to Controller [%s] over MTP [%s] at: %s",
                                  to_id, mtp_param_path, to_addr)
                binding.send_msg(msg.SerializeToString(), to_addr)
            else:
                self._logger.warning("Could not send a Value Change Notification to an unknown Controller [%s]", to_id)
        else:
            self._logger.warning("Could not send ValueChange Notification to an unknown Controller/MTP [%s]",
                                 mtp_param_path)
