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
import zeroconf


class Announcer(object):
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
