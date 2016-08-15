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

# File Name: request_handler.py
#
# Description: USP Request Handler for Agents
#
# Functionality:
#   Class: USPRequestHandler(object)
#    - __init__(agent_endpoint_id, agent_database, service_map=None, debug=False)
#    - handle_request(msg_payload)
#   Class: ProtocolViolationError(Exception)
#   Class: ProtocolValidationError(Exception)
#
"""


import logging

from agent import utils
from agent import agent_db
from agent import usp_pb2 as usp


TAKE_PICTURE_CAMERA_OP = "Device.Services.HomeAutomation.1.Camera.1.TakePicture()"



class UspRequestHandler(object):
    """A USP Message Handler: to be used by a USP Agent"""
    def __init__(self, endpoint_id, agent_database, service_map=None, debug=False):
        """Initialize the USP Request Handler"""
        self._id = endpoint_id
        self._db = agent_database
        self._service_map = service_map
        self._print_debug_messages = debug

        # Initialize the class logger
        self._logger = logging.getLogger(self.__class__.__name__)


    def handle_request(self, msg_payload):
        """Handle a Request/Response interaction"""
        resp = None
        req = usp.Msg()

        # De-Serialize the payload
        req.ParseFromString(msg_payload)
        self._logger.debug("Incoming payload parsed via Protocol Buffers")

        try:
            # Validate the payload before processing it
            self._validate_request(req)
            self._logger.info("Received a [%s] Request",
                              req.body.request.WhichOneof("request"))

            resp = self._process_request(req)
        except ProtocolValidationError as err:
            err_msg = "USP Message validation failed: {}".format(err)
            self._logger.error("%s", err_msg)
            print(err_msg)
            raise ProtocolViolationError(err_msg)

        return req, resp, resp.SerializeToString()


    def _validate_request(self, req):
        """Validate the incoming message"""
        if not req.IsInitialized():
            raise ProtocolValidationError("Request missing Required Fields")

        if len(req.header.msg_id) <= 0:
            raise ProtocolValidationError("Header missing msg_id")

        if len(req.header.proto_version) <= 0:
            raise ProtocolValidationError("Header missing proto_version")

        if len(req.header.to_id) <= 0:
            raise ProtocolValidationError("Header missing to_id")

        if req.header.to_id != self._id:
            raise ProtocolValidationError("Incorrect to_id")

        if len(req.header.from_id) <= 0:
            raise ProtocolValidationError("Header missing from_id")

        if not req.body.WhichOneof("msg_body") == "request":
            raise ProtocolValidationError("Body doesn't contain a Request element")

        self._logger.info("Incoming request passed validation")

    def _process_request(self, req):
        """Processing the incoming Message and return a Response"""
        to_id = req.header.from_id
        err_msg = "Message Failure: Request body does not match Header msg_type"
        usp_err_msg = utils.UspErrMsg(utils.MessageIdHelper.get_message_id(), to_id, self._id)
        resp = usp_err_msg.generate_error(9000, err_msg)

        if req.header.msg_type == usp.Header.GET:
            # Validate that the Request body matches the Header's msg_type
            if req.body.request.WhichOneof("request") == "get":
                resp = self._process_get(req)
        elif req.header.msg_type == usp.Header.GET_INSTANCES:
            # Validate that the Request body matches the Header's msg_type
            if req.body.request.WhichOneof("request") == "get_instances":
                resp = self._process_get_instances(req)
        elif req.header.msg_type == usp.Header.GET_IMPL_OBJECTS:
            # Validate that the Request body matches the Header's msg_type
            if req.body.request.WhichOneof("request") == "get_impl_objects":
                resp = self._process_get_impl_objects(req)
        elif req.header.msg_type == usp.Header.OPERATE:
            # Validate that the Request body matches the Header's msg_type
            if req.body.request.WhichOneof("request") == "operate":
                resp = self._process_operation(req)
        else:
            err_msg = "Invalid USP Message: unknown command"
            resp = usp_err_msg.generate_error(9000, err_msg)

        return resp

    def _process_get(self, req):
        """Process an incoming Get and generate a GetResp"""
        resp = usp.Msg()
        path_result_list = []
        self._logger.info("Processing a Get Request...")

        # Populate the Response's Header information
        self._populate_resp_header(req, resp, usp.Header.GET_RESP)

        # Process the Parameter Paths in the Get Request
        for req_path in req.body.request.get.param_path:
            path_result = usp.GetResp.RequestedPathResult()
            path_result.requested_path = req_path

            try:
                if req_path.endswith(".") or "*" in req_path or "{" in req_path:
                    # If the path is a partial path or has wild-cards, then get all
                    #  full paths before requesting their values
                    items = self._db.find_params(req_path)

                    for item in items:
                        path_result.result_param_map[item] = str(self._db.get(item))
                else:
                    # If the path is full, then just get its value
                    path_result.result_param_map[req_path] = str(self._db.get(req_path))
            except agent_db.NoSuchPathError:
                self._logger.warning("Invalid Path encountered: %s", req_path)
                path_result.invalid_path = True

            path_result_list.append(path_result)

        resp.body.response.get_resp.req_path_result.extend(path_result_list)

        return resp

    def _process_get_instances(self, req):
        """Process an incoming GetInstances and generate a GetInstancesResp"""
        resp = usp.Msg()
        path_result_list = []
        self._logger.info("Processing a GetInstances Request...")

        # Populate the Response's Header information
        self._populate_resp_header(req, resp, usp.Header.GET_INSTANCES_RESP)

        # Process the Parameter Paths in the GetInstances Request
        for req_path in req.body.request.get_instances.obj_path:
            path_result = usp.GetInstancesResp.RequestedPathResult()
            path_result.requested_path = req_path

            try:
                items = self._db.find_instances(req_path)
                path_result.result_path_list.extend(items)
            except agent_db.NoSuchPathError:
                self._logger.warning("Invalid Path encountered: %s", req_path)
                path_result.invalid_path = True

            path_result_list.append(path_result)

        resp.body.response.get_instances_resp.req_path_result.extend(path_result_list)

        return resp

    def _process_get_impl_objects(self, req):
        """Process an incoming GetImplObjects and generate a GetImplObjectsResp"""
        resp = usp.Msg()
        path_result_list = []
        self._logger.info("Processing a GetImplObjects Request...")

        # Populate the Response's Header information
        self._populate_resp_header(req, resp, usp.Header.GET_IMPL_OBJECTS_RESP)

        # Process the Parameter Paths in the GetImplObjects Request
        for req_impl_obj in req.body.request.get_impl_objects.impl_obj:
            req_path = req_impl_obj.obj_path
            next_level = req_impl_obj.next_level
            path_result = usp.GetImplObjectsResp.RequestedPathResult()
            path_result.requested_path = req_path

            try:
                items = self._db.find_impl_objects(req_path, next_level)
                path_result.result_path_list.extend(items)
            except agent_db.NoSuchPathError:
                self._logger.warning("Invalid Path encountered: %s", req_path)
                path_result.invalid_path = True

            path_result_list.append(path_result)

        resp.body.response.get_impl_objects_resp.req_path_result.extend(path_result_list)

        return resp

    def _process_operation(self, req):
        """Process an incoming Operate and generate a OperateResp"""
        resp = usp.Msg()
        op_result_list = []
        command = req.body.request.operate.command
        product_class = self._db.get("Device.LocalAgent.ProductClass")
        self._logger.info("Processing an Operate Request...")

        # Populate the Response's Header information
        self._populate_resp_header(req, resp, usp.Header.OPERATE_RESP)

        if product_class == "RPi_Camera":
            # Validate that the Operate.command is supported
            if command == TAKE_PICTURE_CAMERA_OP:
                op_result = usp.OperateResp.OperationResult()
                out_arg_map = op_result.req_output_args.output_arg_map
                camera = self._service_map["RPi_Camera"]
                param_map = camera.take_picture()
                for param in param_map:
                    out_arg_map[param] = param_map[param]

                op_result_list.append(op_result)
                resp.body.response.operate_resp.operation_result.extend(op_result_list)
            else:
                # Invalid Command - return an Error
                to_id = req.header.from_id
                err_msg = "Operate Failure: invalid command - {}".format(command)
                usp_err_msg = utils.UspErrMsg(utils.MessageIdHelper.get_message_id(), to_id, self._id)
                resp = usp_err_msg.generate_error(9000, err_msg)
        else:
            # Invalid Command - return an Error
            to_id = req.header.from_id
            err_msg = "Operate Failure: unknown product class - {}".format(product_class)
            usp_err_msg = utils.UspErrMsg(utils.MessageIdHelper.get_message_id(), to_id, self._id)
            resp = usp_err_msg.generate_error(9000, err_msg)

        return resp

    def _populate_resp_header(self, req, resp, msg_type):
        """Populate the Response's Header Information"""
        resp.header.msg_id = req.header.msg_id
        resp.header.msg_type = msg_type
        resp.header.proto_version = "1.0"
        resp.header.to_id = req.header.from_id
        resp.header.from_id = self._id
        # Responses don't get responses, so no need for reply_to_id



class ProtocolViolationError(Exception):
    """A USP Protocol Violation Error"""
    pass


class ProtocolValidationError(Exception):
    """A USP Protocol Violation Error"""
    pass
