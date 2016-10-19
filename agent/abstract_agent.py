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
# File Name: abstract_agent.py
#
# Description: An Abstract USP Agent to be used as a basis for a specific binding
#
# Functionality:
#   Class: AbstractAgent(object)
#     __init__(dm_file, db_file, cfg_file_name, debug=False)
#     get_msg_handler()
#     set_value_change_notif_poller(poller)
#     init_subscriptions()
#     start_listening()
#     clean_up() :: Abstract Method
#     _get_supported_protocol() :: Abstract Method
#     _get_notification_sender(notif, controller_id, controller_param_path) :: Abstract Method
#     _get_periodic_notif_handler(agent_id, controller_id, controller_param_path,
#                                 subscription_id, param_path, periodic_interval) :: Abstract Method
#   Class: AbstractPeriodicNotifHandler(threading.Thread)
#     __init__(thread_name, from_id, to_id, subscription_id, param, periodic_interval)
#     run()
#     _handle_periodic(notif) :: Abstract Method
#   Class: AbstractValueChangeNotifPoller(threading.Thread)
#     __init__(agent_db, poll_duration)
#     run()
#     add_param(param, value_change_notif_details)
#     remove_param(param)
#     _handle_value_change(param, value, notif_details) :: Abstract Method
#   Class: AbstractNotificationSender(threading.Thread)
#     __init__(self, notif):
#     run():
#     _prepare_binding() :: Abstract Method
#     _send_notification(msg) :: Abstract Method
#     _clean_up_binding() :: Abstract Method
#
"""


import time
import logging
import threading
import importlib

from agent import utils
from agent import notify
from agent import agent_db
from agent import request_handler


GPIO_PIN = "gpio.pin"
CAMERA_IMAGE_DIR = "camera.image.dir"



class AbstractAgent(object):
    """An Abstract USP Agent that can be built upon for a specific binding"""
    def __init__(self, dm_file, db_file, cfg_file_name):
        """Initialize the Abstract Agent"""
        self._service_map = {}
        self._periodic_handler_list = []
        self._boot_notif_sender_list = []
        self._cfg_file_name = cfg_file_name
        self._value_change_notif_poller = None
        self._logger = logging.getLogger(self.__class__.__name__)

        self._db = agent_db.Database(dm_file, db_file)
        self._endpoint_id = self._db.get("Device.LocalAgent.EndpointID")

        self._load_services()
        self._msg_handler = request_handler.UspRequestHandler(self._endpoint_id, self._db,
                                                              self._service_map)


    def get_msg_handler(self):
        """Retrieve the Internal Message Handler"""
        return self._msg_handler

    def get_value_change_notif_poller(self):
        """Retrieve the Value Change Notification Poller"""
        return self._value_change_notif_poller

    def set_value_change_notif_poller(self, poller):
        """Set the Value Change Notification Poller"""
        self._value_change_notif_poller = poller


    def init_subscriptions(self):
        """Initialize the Subscription Handling"""
        subscription_instances = self._db.find_instances("Device.LocalAgent.Subscription.")

        for instance in subscription_instances:
            if self._db.get(instance + "Enable"):
                self._handle_subscription(instance)
            else:
                subscription_id = self._db.get(instance + "ID")
                self._logger.info("Skipping disabled Subscription [%s]", subscription_id)

    def start_listening(self):
        """
        Start listening for messages and process them
        NOTE: This does not actually listen to any binding, that needs to be done by the
               class that extends the AbstractAgent by overriding this method
        """
        # Start all of the Boot Notification issuers
        for boot_notif in self._boot_notif_sender_list:
            boot_notif.start()

        # Start all of the Periodic Notification handlers
        for periodic_handler in self._periodic_handler_list:
            periodic_handler.start()

        # Start the Value Change Notification Poller Thread
        if self._value_change_notif_poller is not None:
            self._value_change_notif_poller.start()
        else:
            self._logger.warning("ValueChange Notification Poller isn't configured!")

    def clean_up(self):
        """Clean-up and prepare for shutdown"""
        raise NotImplementedError()


    @staticmethod
    def log_messages(logger, req, resp):
        """Logging Helper Static Method"""
        logger.info("Handled a [%s] Request",
                    req.body.request.WhichOneof("request"))
        if resp.body.HasField("response"):
            logger.info("Sending a [%s] Response",
                        resp.body.response.WhichOneof("response"))
        elif resp.body.HasField("error"):
            logger.info("Responding with an Error")
        else:
            logger.warning("Sending an Unknown Response")


    def _load_services(self):
        """Load Home Automation Services Helpers"""
        product_class = self._db.get("Device.DeviceInfo.ProductClass")
        self._logger.info("Loading Services for Product Class [%s]", product_class)

        if product_class == "RPi_Motion":
            default_cfg = {GPIO_PIN: "4"}
            cfg_mgr = utils.ConfigMgr(self._cfg_file_name, default_cfg)
            gpio_pin = int(cfg_mgr.get_cfg_item(GPIO_PIN))
            target_class = self._get_class(product_class, "agent.motion", "PersistDetectedMotion")
            self._service_map[product_class] = target_class(gpio_pin, self._db)
        elif product_class == "RPi_Camera":
            default_cfg = {CAMERA_IMAGE_DIR: "pictures"}
            cfg_mgr = utils.ConfigMgr(self._cfg_file_name, default_cfg)
            camera_image_dir = cfg_mgr.get_cfg_item(CAMERA_IMAGE_DIR)
            target_class = self._get_class(product_class, "agent.camera", "PersistRecordedImage")
            self._service_map[product_class] = target_class(camera_image_dir, "image", self._db)
            # Also create and start the Camera Web UI
            target_ui_class = self._get_class(product_class, "agent.camera_ui", "ThreadedCameraWebUI")
            camera_ui = target_ui_class(host="0.0.0.0", directory=camera_image_dir)
            camera_ui.start()
        else:
            self._logger.warning("No Services to load for Product Class [%s]", product_class)

    def _get_class(self, name, mod_name, class_name):
        """Retrieve the class instance from the provided property"""
        target_class = None

        self._logger.info("Processing [%s]: Class [%s] within Module [%s]",
                          name, class_name, mod_name)

        # import the module, get the class, and instantiate the class
        try:
            mod = importlib.import_module(mod_name)
            target_class = getattr(mod, class_name)
        except ImportError:
            self._logger.warning("Issue with [%s]: Module [%s] could not be imported... Skipping",
                                 name, mod_name)
        except AttributeError:
            self._logger.warning(
                "Issue with [%s]: Class [%s] within Module [%s] could not be found... Skipping",
                name, class_name, mod_name)

        return target_class

    def _handle_subscription(self, subscription_path):
        """Handle a Subscription object"""
        supported_notifs = ["Boot", "ValueChange", "Periodic"]
        subscription_id = self._db.get(subscription_path + "ID")
        notif_type = self._db.get(subscription_path + "NotifType")
        controller_path = self._db.get(subscription_path + "Recipient")

        if notif_type in supported_notifs:
            if self._db.get(controller_path + "Enable"):
                mtp_path_list = self._get_valid_mtp_paths(controller_path)

                if len(mtp_path_list) > 0:
                    for mtp_path in mtp_path_list:
                        controller_id = self._db.get(controller_path + "EndpointID")

                        if notif_type == "Boot":
                            self._handle_boot(controller_id, mtp_path, subscription_id)
                        elif notif_type == "Periodic":
                            self._handle_periodic(subscription_path, controller_id, mtp_path, subscription_id)
                        elif notif_type == "ValueChange":
                            self._handle_value_change(subscription_path, controller_id, mtp_path, subscription_id)
                else:
                    self._logger.warning(
                        "Skipping Subscription [%s] because there are no enabled/matching MTPs for the controller",
                        subscription_id)
            else:
                self._logger.warning("Skipping Subscription [%s] because it references a disabled controller",
                                     subscription_id)
        else:
            self._logger.warning("Skipping Subscription [%s] because it has an unhandled notification type [%s]",
                                 subscription_id, notif_type)

    def _get_valid_mtp_paths(self, controller_path):
        """Find all valid MTPs that are Enabled and have a matching Protocol on the Controller provided"""
        mtp_path_list = []
        mtp_instances = self._db.find_instances(controller_path + "MTP.")

        for mtp_path in mtp_instances:
            if self._db.get(mtp_path + "Enable"):
                controller_protocol = self._db.get(mtp_path + "Protocol")

                if controller_protocol == self._get_supported_protocol():
                    mtp_path_list.append(mtp_path)

        return mtp_path_list

    def _handle_boot(self, controller_id, mtp_path, subscription_id):
        """Handle a Subscription for a Boot Notification"""
        boot_notif = notify.BootNotification(self._endpoint_id, controller_id,
                                             subscription_id, self._db)
        notif_sender = self._get_notification_sender(boot_notif, controller_id, mtp_path)
        if notif_sender is not None:
            self._boot_notif_sender_list.append(notif_sender)
            self._logger.info("Processed Boot Subscription [%s] for MTP [%s] on Controller [%s]",
                              subscription_id, mtp_path, controller_id)
        else:
            self._logger.warning(
                "Skipping Subscription [%s] because Notification Sender not found",
                subscription_id)

    def _handle_periodic(self, subscription_path, controller_id, mtp_path, subscription_id):
        """Handle a Subscription for a Periodic Notification"""
        ref_param_list = self._db.get(subscription_path + "ReferenceList")
        param_path = ref_param_list.split(",")[0]
        periodic_interval = int(self._db.get(param_path + "PeriodicInterval"))
        periodic_handler = self._get_periodic_notif_handler(self._endpoint_id, controller_id,
                                                            mtp_path, subscription_id,
                                                            param_path, periodic_interval)
        if periodic_handler is not None:
            self._periodic_handler_list.append(periodic_handler)
            self._logger.info("Processed Periodic Subscription [%s] for MTP [%s] on Controller [%s]",
                              subscription_id, mtp_path, controller_id)
        else:
            self._logger.warning(
                "Skipping Subscription [%s] because Periodic Notification Handler not found",
                subscription_id)

    def _handle_value_change(self, subscription_path, controller_id, mtp_path, subscription_id):
        """Handle a Subscription for a ValueChange Notification"""
        ref_list = self._db.get(subscription_path + "ReferenceList")
        ref_param_list = ref_list.split(",")
        if self._value_change_notif_poller is not None:
            for param_path in ref_param_list:
                self._value_change_notif_poller.add_param(param_path, self._endpoint_id,
                                                          controller_id, mtp_path, subscription_id)
                self._logger.info("Processed ValueChange Subscription [%s] for MTP [%s] on Controller [%s] - %s",
                                  subscription_id, mtp_path, controller_id, param_path)
        else:
            self._logger.warning(
                "Skipping Subscription [%s] because ValueChange Notification Poller isn't configured",
                subscription_id)

    def _get_supported_protocol(self):
        """Return the supported Protocol as a String: CoAP, STOMP, HTTP/2, WebSockets"""
        raise NotImplementedError()

    def _get_notification_sender(self, notif, controller_id, mtp_path):
        """Return an instance of a binding specific AbstractNotificationSender"""
        raise NotImplementedError()

    def _get_periodic_notif_handler(self, agent_id, controller_id, mtp_path,
                                    subscription_id, param_path, periodic_interval):
        """Return an instance of a binding specific AbstractPeriodicNotifHandler"""
        raise NotImplementedError()



class AbstractPeriodicNotifHandler(threading.Thread):
    """An Abstract Periodic Notification Handler that is extended for specific bindings such that
        a Periodic Notification is issued via the appropriate binding every Interval"""
    def __init__(self, database, thread_name, from_id, to_id, subscription_id, param):
        """Initialize the Periodic Notification Handler"""
        threading.Thread.__init__(self, name="PeriodicNotifHandler-" + thread_name)
        self._db = database
        self._param = param
        self._to_id = to_id
        self._from_id = from_id
        self._subscription_id = subscription_id
        self._logger = logging.getLogger(self.__class__.__name__)


    def run(self):
        """Thread execution code - issue a Periodic Notification every periodic_interval seconds"""
        binding_exists = True
        periodic_interval_param_name = self._param + "PeriodicInterval"

        while binding_exists:
            try:
                periodic_interval = int(self._db.get(periodic_interval_param_name))
                self._logger.info("Waiting %d seconds before next Periodic Notification", periodic_interval)
                time.sleep(periodic_interval)

                self._logger.info("Sending a Periodic Notification to %s", self._to_id)
                notif = notify.PeriodicNotification(self._from_id, self._to_id,
                                                    self._subscription_id, self._param)
                binding_exists = self._handle_periodic(notif)
            except agent_db.NoSuchPathError:
                binding_exists = False
                self._logger.warning("Periodic Notification Failure : No Periodic Interval [%s]",
                                     periodic_interval_param_name)

        self._logger.warning("Periodic Notification Handler named [%s] shutting down", self.name)


    def _handle_periodic(self, notif):
        """Handle the Binding Specific Periodic Notification"""
        raise NotImplementedError()



class AbstractValueChangeNotifPoller(threading.Thread):
    """An Abstract Value Change Notification Poller that is extended for specific bindings such that
        ValueChange Notifications can be issued when a Parameter's Value has Changed"""
    TO_ID = "to.id"
    FROM_ID = "from.id"
    MTP = "mtp.path"
    SUBSCRIPTION_ID = "subscription.id"

    def __init__(self, agent_database, poll_duration=0.5):
        """Initialize the Value Change Notification Poller Thread"""
        threading.Thread.__init__(self, name="ValueChangeNotifPoller")
        self._db = agent_database
        self._param_cache = {}
        self._param_poll_list = []
        self._notif_details_dict = {}
        self._cache_lock = threading.Lock()
        self._poll_duration = poll_duration
        self._logger = logging.getLogger(self.__class__.__name__)


    def run(self):
        """Thread execution code - poll for a value change and then
             send the ValueChange Notification"""
        while True:
            time.sleep(self._poll_duration)

            for param in self._param_poll_list:
                self._logger.debug("Checking %s for a Value Change", param)
                value = self._db.get(param)
                with self._cache_lock:
                    if value != self._param_cache[param]:
                        self._logger.info("Value Change detected for %s", param)
                        self._param_cache[param] = value
                        notif_details = self._notif_details_dict[param]
                        to_id = notif_details[self.TO_ID]
                        from_id = notif_details[self.FROM_ID]
                        subscription_id = notif_details[self.SUBSCRIPTION_ID]
                        mtp_param_path = notif_details[self.MTP]
                        self._handle_value_change(param, value, to_id, from_id,
                                                  subscription_id, mtp_param_path)

    def add_param(self, param, agent_id, controller_id, mtp_param_path, subscription_id):
        """Add a Parameter to the Polling List"""
        self._logger.info("Adding %s to the ValueChange Notification Poller", param)
        value_change_notif_details_dict = {}
        value_change_notif_details_dict[self.FROM_ID] = agent_id
        value_change_notif_details_dict[self.TO_ID] = controller_id
        value_change_notif_details_dict[self.SUBSCRIPTION_ID] = subscription_id
        value_change_notif_details_dict[self.MTP] = mtp_param_path

        with self._cache_lock:
            self._param_cache[param] = self._db.get(param)
            self._param_poll_list.append(param)
            self._notif_details_dict[param] = value_change_notif_details_dict

    def remove_param(self, param):
        """Remove a Parameter from the Polling List"""
        self._logger.info("Removing %s from the ValueChange Notification Poller", param)
        with self._cache_lock:
            del self._param_cache[param]
            self._param_poll_list.remove(param)
            del self._notif_details_dict[param]


    def _handle_value_change(self, param, value, to_id, from_id, subscription_id, mtp_param_path):
        """Handle the Binding Specific Value Change Processing"""
        raise NotImplementedError()



class AbstractNotificationSender(threading.Thread):
    """An Abstract Notification Sender that is extended for a specific binding"""
    def __init__(self, notif):
        """Initialize the Abstract Notification Sender"""
        threading.Thread.__init__(self, name="NotificationSender")
        self._notif = notif
        self._logger = logging.getLogger(self.__class__.__name__)


    def run(self):
        """Thread execution code - send the Notification"""
        msg = self._notif.generate_notif_msg()
        self._prepare_binding()
        self._send_notification(msg)
        self._clean_up_binding()


    def _prepare_binding(self):
        """Perform actions needed to create a binding or prepare an existing binding to send a message"""
        raise NotImplementedError()

    def _send_notification(self, msg):
        """Send the notification via the binding"""
        raise NotImplementedError()

    def _clean_up_binding(self):
        """Perform actions needed to delete a binding or clean-up an existing binding that sent the message"""
        raise NotImplementedError()
