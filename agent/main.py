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
# File Name: main.py
#
# Description: The main method to start a STOMP USP Agent
#
# Functionality:
#   Class: Agent(stomp_agent.StompAgent)
#     __init__(cfg_file_name, log_file_name, log_level=logging.INFO, debug=False)
#
"""


import logging
import argparse
import prometheus_client

from agent import coap_agent
from agent import stomp_agent



class Agent:
    """A USP Agent Wrapper"""
    def __init__(self, cfg_file_name, log_file_name, log_level=logging.INFO):
        """Initialize the Agent"""
        debug = (log_level == logging.DEBUG)
        logging.basicConfig(filename=log_file_name, level=log_level,
                            format='%(asctime)-15s %(name)s %(levelname)-8s %(message)s')

        # Handle Command Line Arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--coap", action="store_true",
                            help="use the CoAP Binding instead of the STOMP Binding")
        parser.add_argument("--coap-port", action="store", nargs="?",
                            type=int, default=5683,
                            help="specify the CoAP Port to listen on")
        parser.add_argument("--intf", action="store", nargs="?",
                            type=str, default="",
                            help="specify the network interface to use")
        parser.add_argument("-t", "--client-type", action="store", nargs="?",
                            default="test",
                            help="specify the type of client (e.g. test, camera, motion)")
        parser.add_argument("--version", action="version",
                            version='%(prog)s 0.1a',
                            help="show the version of this tool")
        args = parser.parse_args()
        client_type = args.client_type
        use_coap = args.coap
        coap_port = args.coap_port
        net_intf = args.intf

        dm_file_name = "database/{}-dm.json".format(client_type)
        db_file_name = "database/{}.db".format(client_type)

        prometheus_client.start_http_server(9001)

        if use_coap:
            logging.info("#######################################################")
            logging.info("## Starting a CoAP USP Agent                         ##")
            logging.info("#######################################################")

            my_coap_agent = coap_agent.CoapAgent(dm_file_name, db_file_name, net_intf, coap_port, cfg_file_name, debug)
            my_coap_agent.start_listening()
            my_coap_agent.clean_up()
        else:
            logging.info("#######################################################")
            logging.info("## Starting a STOMP USP Agent                        ##")
            logging.info("#######################################################")

            my_stomp_agent = stomp_agent.StompAgent(dm_file_name, db_file_name, net_intf, cfg_file_name, debug)
            my_stomp_agent.start_listening()
            my_stomp_agent.clean_up()



def main():
    """Main Processing for USP Agent"""
    Agent("cfg/agent.json", "logs/agent.log")
#    Agent("cfg/agent.json", "logs/agent.log", log_level=logging.DEBUG)



if __name__ == "__main__":
    main()
