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
#   Class: CoapBindingListener(threading.Thread)
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
        abstract_agent.AbstractAgent.__init__(self, dm_file, db_file, net_intf, cfg_file_name)
        self._can_start = True

        # Initialize the underlying Agent DB MTP details for CoAP
        resource_path = 'usp'
        ip_addr = self._get_ip_addr(net_intf)
        if ip_addr is not None:
            url = "coap://" + ip_addr + ":" + str(port) + "/" + resource_path
            self._db.update("Device.LocalAgent.MTP.1.Enable", True)   # Enable the CoAP MTP
            self._db.update("Device.LocalAgent.MTP.1.CoAP.URL", url)  # Set the CoAP MTP URL
            self._db.update("Device.LocalAgent.MTP.2.Enable", False)  # Disable the STOMP MTP
            self._logger.info("Listening at URL: %s", url)

            self._binding = coap_usp_binding.CoapUspBinding(port, resource_path=resource_path, debug=debug)
            self._binding.listen(self._endpoint_id)

            self._mdns_announcer = mdns.Announcer(ip_addr, port, resource_path, self._endpoint_id)
            self._mdns_announcer.announce(self._get_friendly_name(), self._get_subtypes())

            value_change_notif_poller = CoapValueChangeNotifPoller(self._db)
            value_change_notif_poller.set_binding(self._binding)
            self.set_value_change_notif_poller(value_change_notif_poller)

            self.init_subscriptions()
        else:
            self._can_start = False
            self._logger.error("IP Address could not be found for provided Network Interface [%s] - EXITING",
                               net_intf)


    def start_listening(self, timeout=15):
        """Start listening for messages and process them"""
        if self._can_start:
            abstract_agent.AbstractAgent.start_listening(self)

            msg_handler = self.get_msg_handler()
            listener = CoapBindingListener("CoAP", self._db, self._binding, msg_handler, timeout)
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

    def _get_notification_sender(self, notif, controller_id, mtp_param_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        controller_url = self._db.get(mtp_param_path + "CoAP.URL")
        return abstract_agent.NotificationSender(notif, self._binding, controller_url)

    def _get_periodic_notif_handler(self, agent_id, controller_id, mtp_param_path,
                                    subscription_id, param_path):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        controller_url = self._db.get(mtp_param_path + "CoAP.URL")
        periodic_notif_handler = CoapPeriodicNotifHandler(self._db, mtp_param_path, agent_id, controller_id,
                                                          subscription_id, param_path, controller_url)
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



class CoapBindingListener(abstract_agent.BindingListener):
    """A CoAP Specific implementation of an Abstract BindingListener"""
    def __init__(self, thread_name, database, binding, msg_handler, timeout=15):
        """Initialize the STOMP Binding Listener"""
        abstract_agent.BindingListener.__init__(self, thread_name, binding, msg_handler, timeout)
        self._db = database


    def _get_addr_from_id(self, to_endpoint_id):
        """CoAP Specific implementation of how to get an Endpoint Address from an Endpoint ID"""
        controller_instances = self._db.find_instances("Device.LocalAgent.Controller.")

        for controller_path in controller_instances:
            controller_id = self._db.get(controller_path + "EndpointID")
            if controller_id == to_endpoint_id:
                if self._db.get(controller_path + "Enable"):
                    return self._get_addr_from_mtps(controller_id, controller_path)
                else:
                    self._logger.warning("Can not retrieve CoAP URL for Controller [%s] because it is Disabled",
                                         controller_id)
            else:
                self._logger.debug("Skipping Controller [%s] - Endpoint ID doesn't match: %s",
                                   controller_id, to_endpoint_id)

        return None

    def _get_addr_from_mtps(self, controller_id, controller_path):
        mtp_instances = self._db.find_instances(controller_path + "MTP.")

        for mtp_path in mtp_instances:
            if self._db.get(mtp_path + "Enable"):
                protocol = self._db.get(mtp_path + "Protocol")

                if protocol == self._get_supported_protocol():
                    return self._db.get(mtp_path + "CoAP.URL")
                else:
                    mtp_name = self._db.get(mtp_path + "Name")
                    self._logger.info("Skipping MTP [%s] on Controller [%s] - Wrong Protocol", mtp_name, controller_id)
            else:
                mtp_name = self._db.get(mtp_path + "Name")
                self._logger.info("Skipping MTP [%s] on Controller [%s] - Disabled", mtp_name, controller_id)

        return None

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        return "CoAP"



class CoapPeriodicNotifHandler(abstract_agent.AbstractPeriodicNotifHandler):
    """Issue a Periodic Notifications via a CoAP Binding"""
    def __init__(self, database, mtp_param_path, from_id, to_id, subscription_id, param, controller_url):
        """Initialize the CoAP Periodic Notification Handler"""
        abstract_agent.AbstractPeriodicNotifHandler.__init__(self, database, mtp_param_path,
                                                             from_id, to_id, subscription_id, param)
        self._binding = None
        self._mtp_param_path = mtp_param_path
        self._controller_url = controller_url


    def set_binding(self, binding):
        """Configure the CoAP Binding to use when sending the Notification"""
        self._binding = binding

    def _handle_periodic(self, notif):
        """Handle the CoAP Periodic Notification"""
        msg = notif.generate_notif_msg()

        if self._binding is not None:
            self._logger.info("Sending a Periodic Notification to ID [%s] over MTP [%s] at: %s",
                              self._to_id, self._mtp_param_path, self._controller_url)
            self._binding.send_msg(msg.SerializeToString(), self._controller_url)
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
        controller_url = self._db.get(mtp_param_path + "CoAP.URL")
        msg = notif.generate_notif_msg()

        self._logger.info("Sending a ValueChange Notification to ID [%s] over MTP [%s] at: %s",
                          to_id, mtp_param_path, controller_url)
        self._binding.send_msg(msg.SerializeToString(), controller_url)
