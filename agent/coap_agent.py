# Copyright (c) 2016-2017 John Blackford
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
# File Name: coap_agent.py
#
# Description: A CoAP USP Agent
#
# Functionality:
#   Class: CoapAgent(abstract_agent.AbstractAgent)
#     __init__(dm_file, db_file, cfg_file_name="cfg/agent.json", debug=False)
#     start_listening(timeout=15)
#     clean_up()
#   Class: CoapPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler)
#     __init__(database, mtp_param_path, from_id, to_id, subscription_id, param, controller_url)
#     set_binding(binding)
#   Class: CoapValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller)
#     __init__(agent_db, poll_duration=0.5)
#     set_binding(binding)
#
"""


from agent import mdns
from agent import utils
from agent import notify
from agent import agent_db
from agent import abstract_agent
from agent import coap_usp_binding


class CoapAgent(abstract_agent.AbstractAgent):
    """A USP Agent that uses the CoAP Binding"""
    def __init__(self, dm_file, db_file, net_intf, port=5683, cfg_file_name="cfg/agent.json", debug=False):
        """Initialize the CoAP Agent"""
        abstract_agent.AbstractAgent.__init__(self, dm_file, db_file, net_intf, cfg_file_name, debug)
        self._can_start = True

        # Initialize the underlying Agent DB MTP details for CoAP
        resource_path = 'usp'
        ip_addr = self._get_ip_addr(net_intf)
        if ip_addr is not None:
            url = "coap://" + ip_addr + ":" + str(port) + "/" + resource_path
            num_local_agent_coap_mtps = self._init_db_for_mtp(ip_addr, port, resource_path)

            # We only support 1 Local Agent CoAP MTP
            if num_local_agent_coap_mtps == 1:
                self._binding = coap_usp_binding.CoapUspBinding(ip_addr, self._endpoint_id, port,
                                                                resource_path=resource_path, debug=debug)
                self._binding.listen(url)

                self._mdns_announcer = mdns.Announcer(ip_addr, port, resource_path, self._endpoint_id)
                self._mdns_announcer.announce(self._get_friendly_name(), self._get_subtypes())

                value_change_notif_poller = CoapValueChangeNotifPoller(self._db)
                value_change_notif_poller.set_binding(self._binding)
                self.set_value_change_notif_poller(value_change_notif_poller)

                self.init_subscriptions()
            else:
                self._can_start = False
                self._logger.error("The Agent must have 1 and only 1 CoAP Local Agent MTP , %s were found - EXITING",
                                   str(num_local_agent_coap_mtps))
        else:
            self._can_start = False
            self._logger.error("IP Address could not be found for provided Network Interface [%s] - EXITING",
                               net_intf)

    def start_listening(self, timeout=15):
        """Start listening for messages and process them"""
        if self._can_start:
            abstract_agent.AbstractAgent.start_listening(self)

            msg_handler = self.get_msg_handler()
            listener = abstract_agent.BindingListener("CoAP", self._binding, msg_handler, timeout)
            listener.start()
            listener.join()

    def clean_up(self):
        """Clean up the USP Binding"""
        if self._can_start:
            self._binding.clean_up()

    def _get_ip_addr(self, net_intf):
        """Get the IP Address for this Agent"""
        if len(net_intf) > 1:
            ip_addr = utils.IPAddr.get_ip_addr(net_intf)
        else:
            ip_addr = utils.IPAddr.get_ip_addr()

        return ip_addr

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        return "CoAP"

    def _init_db_for_mtp(self, host, port, path):
        """Enable the LocalAgent MTPs for the supported protocol and Disable all other LocalAgent MTPs"""
        coap_mtp_count = 0
        agent_mtp_instances = self._db.find_instances("Device.LocalAgent.MTP.")

        for agent_mtp_path in agent_mtp_instances:
            if self._db.get(agent_mtp_path + "Protocol") == self._get_supported_protocol():
                coap_mtp_count += 1
                self._db.update(agent_mtp_path + "Enable", True)
                self._db.update(agent_mtp_path + "CoAP.Host", host)
                self._db.update(agent_mtp_path + "CoAP.Port", str(port))
                self._db.update(agent_mtp_path + "CoAP.Path", path)
            else:
                self._db.update(agent_mtp_path + "Enable", False)

        return coap_mtp_count

    def _get_notification_sender(self, notif, controller_id, mtp_param_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        controller_url = "coap://" + self._db.get(mtp_param_path + "CoAP.Host") + ":" + \
                         str(self._db.get(mtp_param_path + "CoAP.Port")) + "/" + \
                         self._db.get(mtp_param_path + "CoAP.Path")
        # TODO: Make sure to substitiute the Host with mdns resolution
        return abstract_agent.NotificationSender(notif, self._binding, controller_url)

    def _get_periodic_notif_handler(self, agent_id, controller_id, mtp_param_path,
                                    subscription_id, param_path):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        periodic_notif_handler = CoapPeriodicNotifHandler(self._db, mtp_param_path, agent_id, controller_id,
                                                          subscription_id, param_path)
        periodic_notif_handler.set_binding(self._binding)
        return periodic_notif_handler

    def _get_friendly_name(self):
        """Retrieve the Friendly Name of the Agent for use in mDNS advertising"""
        friendly_name = None

        try:
            friendly_name = self._db.get("Device.DeviceInfo.FriendlyName")
        except agent_db.NoSuchPathError:
            self._logger.warning("Can't retrieve 'Friendly Name' for mDNS advertising")

        return friendly_name

    def _get_subtypes(self):
        """Retrieve the Device Advertised Subtypes of the Agent for use in mDNS advertising"""
        subtypes = None

        try:
            subtypes = self._db.get("Device.LocalAgent.AdvertisedDeviceSubtypes")
        except agent_db.NoSuchPathError:
            self._logger.warning("Can't retrieve 'Advertised Device Subtypes' for mDNS advertising")

        return subtypes


class CoapPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler):
    """Issue a Periodic Notifications via a CoAP Binding"""
    def __init__(self, database, mtp_param_path, from_id, to_id, subscription_id,
                 path_to_periodic_params):
        """Initialize the CoAP Periodic Notification Handler"""
        abstract_agent.AbstractPeriodicNotifHandler.__init__(self, database, mtp_param_path,
                                                             from_id, to_id, subscription_id,
                                                             path_to_periodic_params)
        self._mtp_param_path = mtp_param_path

    def _handle_periodic_record(self, notif_record):
        """Handle the CoAP Periodic Notification"""
        if self._binding is not None:
            controller_url = "coap://" + self._db.get(self._mtp_param_path + "CoAP.Host") + ":" + \
                             str(self._db.get(self._mtp_param_path + "CoAP.Port")) + "/" + \
                             self._db.get(self._mtp_param_path + "CoAP.Path")
            # TODO: Make sure to substitiute the Host with mdns resolution
            self._logger.info("Sending a Periodic Notification to ID [%s] over MTP [%s] at: %s",
                              self._to_id, self._mtp_param_path, controller_url)
            self._binding.send_msg(notif_record.SerializeToString(), controller_url)
        else:
            self._logger.warning("Unable to send the Periodic Notification - No Binding")

        return True


class CoapValueChangeNotifPoller(abstract_agent.AbstractValueChangeNotifPoller):
    """Poll Parameters for Value Change Notifications via a CoAP Binding"""
    def __init__(self, agent_database, poll_duration=0.5):
        """Initialize the STOMP Value Change Notification Poller"""
        abstract_agent.AbstractValueChangeNotifPoller.__init__(self, agent_database, poll_duration)
        self._binding = None

    def set_binding(self, binding):
        """Configure the CoAP Binding to use when sending the Notification"""
        self._binding = binding

    def _handle_value_change(self, param, value, to_id, from_id, subscription_id, mtp_param_path):
        """Handle the Binding Specific Value Change Processing"""
        notif = notify.ValueChangeNotification(from_id, to_id, subscription_id, param, value)
        controller_url = "coap://" + self._db.get(mtp_param_path + "CoAP.Host") + ":" + \
                         str(self._db.get(mtp_param_path + "CoAP.Port")) + "/" + \
                         self._db.get(mtp_param_path + "CoAP.Path")
        # TODO: Make sure to substitiute the Host with mdns resolution
        notif_record = notif.wrap_notif_in_record(notif.generate_notif_msg())

        self._logger.info("Sending a ValueChange Notification to ID [%s] over MTP [%s] at: %s",
                          to_id, mtp_param_path, controller_url)
        self._binding.send_msg(notif_record.SerializeToString(), controller_url)
