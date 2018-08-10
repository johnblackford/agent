# Copyright (c) 2017 John Blackford
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
# File Name: mdns.py
#
# Description: An mDNS implementation for a USP Agent using the zeroconf library
#
# Class Structure:
#  - Announcer(object)
#    - __init__(ip_addr, coap_port, coap_resource_path, usp_endpoint_id)
#    - announce()
#    - clean_up()
#
"""


import socket
import logging
import zeroconf


class Announcer:
    """Announce a CoAP Agent via mDNS"""
    def __init__(self, ip_addr, coap_port, coap_resource_path, usp_endpoint_id):
        """Initialize the Announcer class"""
        self._zconf = None
        self._ip_addr = ip_addr
        self._port = coap_port
        self._resource_path = coap_resource_path
        self._instance = usp_endpoint_id
        self._service = "_usp-agt-coap._udp."
        self._domain = "local."

    def announce(self, friendly_name=None, subtypes=None):
        """Announce myself on mDNS by registering a service"""
        svc_type = self._service + self._domain
        svc_name = self._instance + "." + self._service + self._domain
        svc_addr = socket.inet_aton(self._ip_addr)
        svc_port = self._port
        svc_server = self._instance + "." + self._domain
        svc_props = {"path": self._resource_path}

        if friendly_name is not None:
            svc_props["name"] = friendly_name

        if subtypes is not None:
            svc_props["type"] = subtypes

        srv = zeroconf.ServiceInfo(svc_type, svc_name, svc_addr, svc_port, properties=svc_props, server=svc_server)
        self._zconf = zeroconf.Zeroconf(interfaces=zeroconf.InterfaceChoice.Default)
        self._zconf.register_service(srv)

    def cleanup(self):
        """Clean up the ZeroConf object"""
        self._zconf.close()


class Listener:
    """Listen for CoAP Controllers via mDNS"""
    def __init__(self):
        """Initialize the Listener Class"""
        self._zconf = None
        self._browser = None
        self._host_name_to_ip_map = {}
        self._endpoint_id_to_url_map = {}
        self._service = "_usp-ctl-coap._udp.local."
        self._logger = logging.getLogger(self.__class__.__name__)

    def listen(self):
        """Listen for mDNS registrations against a specific service"""
        self._zconf = zeroconf.Zeroconf(interfaces=zeroconf.InterfaceChoice.Default)
        self._browser = zeroconf.ServiceBrowser(self._zconf, self._service, self)

    def add_service(self, zconf, svc_type, name):
        """Process an incoming mDNS Service Registration"""
        info = zconf.get_service_info(svc_type, name)
        self._logger.info("Processing an mDNS Service Registration for [%s]: %s", name, info)

        controller_coap_url = self._get_coap_url(info)
        controller_endpoint_id = self._get_endpoint_id(name)
        self._logger.info("mDNS Service Registration for [%s] resolved to Endpoint ID [%s] and CoAP URL [%s]",
                          name, controller_endpoint_id, controller_coap_url)

        if controller_endpoint_id in self._endpoint_id_to_url_map:
            self._logger.info("mDNS Service Registration for [%s] updated the URL for Endpoint ID [%s] to: %s",
                              name, controller_endpoint_id, controller_coap_url)
        else:
            self._logger.info("mDNS Service Registration for [%s] created an entry for Endpoint ID [%s] with: %s",
                              name, controller_endpoint_id, controller_coap_url)
        self._endpoint_id_to_url_map[controller_endpoint_id] = controller_coap_url
        self._host_name_to_ip_map[name] = socket.inet_ntoa(info.address)

    def remove_service(self, zconf, svc_type, name):
        """Process an incoming mDNS Service De-Registration"""
        self._logger.debug("Service [%s] was Removed", name)
        controller_endpoint_id = self._get_endpoint_id(name)
        self._logger.info("mDNS Service De-Registration caused Endpoint ID [%s] to be removed",
                          controller_endpoint_id)
        del self._endpoint_id_to_url_map[controller_endpoint_id]
        del self._host_name_to_ip_map[name]

    def resolve_addr(self, endpoint_id):
        """Retrieve the current CoAP URL for a given USP Endpoint ID"""
        url = None

        if endpoint_id in self._endpoint_id_to_url_map:
            url = self._endpoint_id_to_url_map[endpoint_id]

        return url

    def resolve_host(self, host_name):
        """Retrieve the IP Address for the provided Host Name"""
        ip_addr = None

        if host_name in self._host_name_to_ip_map:
            ip_addr = self._host_name_to_ip_map[host_name]

        return ip_addr

    def cleanup(self):
        """Clean up the ZeroConf object"""
        self._browser.cancel()
        self._zconf.close()

    def _get_coap_url(self, info):
        """Build a CoAP URL for the Controller based on the Service Info provided"""
        coap_url = None
        port = str(info.port)
        addr = socket.inet_ntoa(info.address)
        resource_path = info.properties.get(b'path')

        if resource_path is not None:
            decoded_resource_path = resource_path.decode('ascii')
            coap_url = "coap://" + addr + ":" + port + "/" + decoded_resource_path
        else:
            self._logger.warning("Discovered a malformed CoAP Controller - No 'path' Property")

        return coap_url

    def _get_endpoint_id(self, name):
        """Retrieve the USP Endpoint ID from the mDNS Name"""
        return name.split(".")[0]
