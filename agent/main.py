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

from agent import stomp_agent



class Agent(stomp_agent.StompAgent):
    """A STOMP Agent Wrapper"""
    def __init__(self, cfg_file_name, log_file_name, log_level=logging.INFO, debug=False):
        """Initialize the Agent"""
        logging.basicConfig(filename=log_file_name, level=log_level,
                            format='%(asctime)-15s %(name)s %(levelname)-8s %(message)s')

        logging.info("#######################################################")
        logging.info("## Starting a USP Agent                              ##")
        logging.info("#######################################################")

        # Handle Command Line Arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--client-type", action="store", nargs="?",
                            default="test",
                            help="specify the type of client (e.g. test, camera, motion)")
        parser.add_argument("--version", action="version",
                            version='%(prog)s 0.1a',
                            help="show the version of this tool")
        args = parser.parse_args()
        client_type = args.client_type

        dm_file_name = "database/{}-dm.json".format(client_type)
        db_file_name = "database/{}.db".format(client_type)

        stomp_agent.StompAgent.__init__(self, dm_file_name, db_file_name, cfg_file_name, debug)
        stomp_agent.start_listening()
        stomp_agent.clean_up()


def main():
    """Main Processing for USP Agent"""
    Agent("cfg/agent.json", "logs/agent.log")



if __name__ == "__main__":
    main()