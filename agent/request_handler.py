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


import re
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
        usp_err_msg = utils.UspErrMsg(req.header.msg_id, to_id, self._id)
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
        elif req.header.msg_type == usp.Header.SET:
            # Validate that the Request body matches the Header's msg_type
            if req.body.request.WhichOneof("request") == "set":
                resp = self._process_set(req)
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

    def _process_set(self, req):
        """Process an incoming Set and generate a SetResp"""
        resp = usp.Msg()
        path_to_set_dict = {}
        update_obj_result_list = []
        set_failure_param_err_list = []
        usp_err_msg = utils.UspErrMsg(req.header.msg_id, req.header.from_id, self._id)

        # Populate the Response's Header information
        self._populate_resp_header(req, resp, usp.Header.SET_RESP)

        # Retrieve the all_partial flag from the request
        allow_partial_updates = req.body.request.set.allow_partial

        # Loop through each UpdateObject
        for obj_to_update in req.body.request.set.update_obj:
            param_err_list = []
            update_inst_result_list = []
            obj_path_set_failure_err_dict = {}
            obj_path_to_update = obj_to_update.obj_path
            auto_create_obj = obj_to_update.auto_create

            try:
                affected_path_list = self._get_affected_paths(obj_path_to_update, auto_create_obj)

                # For each Affected Path, update the Parameter Settings
                for affected_path in affected_path_list:
                    update_inst_result = usp.SetResp.UpdatedInstanceResult()
                    update_inst_result.affected_path = affected_path

                    set_failure_err_list = self._validate_params(affected_path, obj_to_update, path_to_set_dict,
                                                                 update_inst_result, param_err_list)
                    if len(set_failure_err_list) > 0:
                        obj_path_set_failure_err_dict[affected_path] = set_failure_err_list

                    update_inst_result_list.append(update_inst_result)

                print("Processed all affected paths for {}".format(obj_path_to_update))
                print("Found {} items in the obj_path_set_failure_dict: {}".format(len(obj_path_set_failure_err_dict), obj_path_set_failure_err_dict))
                # If there were no Set Failure errors for the obj_to_update, oper_success
                if len(obj_path_set_failure_err_dict) == 0:
                    update_obj_result = usp.SetResp.UpdatedObjectResult()
                    update_obj_result.requested_path = obj_path_to_update
                    update_obj_result.oper_status.oper_success.param_err.extend(param_err_list)
                    update_obj_result.oper_status.oper_success.updated_inst_result.extend(update_inst_result_list)
                    update_obj_result_list.append(update_obj_result)
                    print("Updated the update_obj_result_list for {}".format(obj_path_to_update))
                else:
                    # If there were Set Failure errors for the obj_to_update
                    if allow_partial_updates:
                        # Set Failures are handled via oper_failure on the SetResp
                        err_msg = "Failed to Set Required Parameters: "

                        for affected_path in obj_path_set_failure_err_dict:
                            for param_name in obj_path_set_failure_err_dict[affected_path]:
                                err_msg = err_msg + affected_path + param_name + " "

                        update_obj_result = usp.SetResp.UpdatedObjectResult()
                        update_obj_result.requested_path = obj_path_to_update
                        update_obj_result.oper_status.oper_failure.err_code = 9000
                        update_obj_result.oper_status.oper_failure.err_msg = err_msg
                        update_obj_result_list.append(update_obj_result)
                    else:
                        # Set Failures are handled via ParamError on an Error message
                        for affected_path in obj_path_set_failure_err_dict:
                            for param_name in obj_path_set_failure_err_dict[affected_path]:
                                set_failure_param_err = usp.Error.ParamError()
                                set_failure_param_err.param_path = affected_path + param_name
                                set_failure_param_err.err_code = 9000
                                set_failure_param_err.err_msg = "Failed to Set Required Parameter"
                                set_failure_param_err_list.append(set_failure_param_err)
            except SetValidationError as sv_err:
                if allow_partial_updates:
                    # Invalid Path Found, Allow Partial Updates = True :: Fail this one object path
                    update_obj_result = usp.SetResp.UpdatedObjectResult()
                    update_obj_result.requested_path = obj_path_to_update
                    update_obj_result.oper_status.oper_failure.err_code = sv_err.get_error_code()
                    update_obj_result.oper_status.oper_failure.err_msg = sv_err.get_error_message()
                    update_obj_result_list.append(update_obj_result)
                else:
                    # Invalid Path Found, Allow Partial Updates = False :: Fail the entire Set
                    set_failure_param_err = usp.Error.ParamError()
                    set_failure_param_err.param_path = obj_path_to_update
                    set_failure_param_err.err_code = sv_err.get_error_code()
                    set_failure_param_err.err_msg = sv_err.get_error_message()
                    set_failure_param_err_list.append(set_failure_param_err)

        if len(set_failure_param_err_list) > 0:
            err_code = 9000
            err_msg = "Invalid Path Found, Allow Partial Updates = False :: Fail the entire Set"
            resp = usp_err_msg.generate_error(err_code, err_msg)
            resp.body.error.param_err.extend(set_failure_param_err_list)
        else:
            # Process the Updates against the database
            for param_path in path_to_set_dict:
                value_to_set = path_to_set_dict[param_path]
                self._db.update(param_path, value_to_set)

            resp.body.response.set_resp.updated_obj_result.extend(update_obj_result_list)

        return resp

    def _get_affected_paths(self, obj_path_to_update, auto_create_obj):
        """
          Retrieve the affected paths based on the incoming obj_path:
            - Retrieve existing Paths (including general validation and that it is supported)
              - If no Paths exist then consider the auto_create flag :: SetValidationError raised if anything fails
        """
        is_static_path = self._is_set_path_static(obj_path_to_update)
        is_search_path = self._is_set_path_searching(obj_path_to_update)

        try:
            affected_path_list = self._db.find_objects(obj_path_to_update)

            if len(affected_path_list) == 0:
                if auto_create_obj:
                    if is_search_path or is_static_path:
                        pass
                    else:
                        # The obj_path doesn't exist, but auto_create is enabled so create the instance
                        affected_path_list = self._auto_create_set_path(obj_path_to_update)
                else:
                    err_code = 9000
                    err_msg = "Non-existent obj_path encountered (auto_create disabled)- {}".format(obj_path_to_update)
                    raise SetValidationError(err_code, err_msg)
        except agent_db.NoSuchPathError:
            err_code = 9000
            err_msg = "Invalid obj_path encountered - {}".format(obj_path_to_update)
            raise SetValidationError(err_code, err_msg)

        return affected_path_list

    def _is_set_path_static(self, obj_path_to_update):
        """
          Check to see tha the obj_path_to_update doesn't contain:
            - Instance Number based addressing elements
            - FUTURE: Unique Key based addressing elements
            - wildcard-based searching elements
            - FUTURE: expression-based searching elements
        """
        if not self._is_set_path_searching(obj_path_to_update):
            pattern = re.compile(r'\.[0-9]+\.')
            if pattern.search(obj_path_to_update) is None:
                return True

        return False

    def _is_set_path_searching(self, obj_path_to_update):
        """
          Check to see if the obj_path_to_update contains:
            - wildcard-based searching elements
            - FUTURE: expression-based searching elements
        """
        return ".*." in obj_path_to_update

    def _auto_create_set_path(self, obj_path_to_update):
        """
          Automatically Create the obj_path_to_update with the supplied inst_ident:
            - Unless the inst_ident is an instance number, then create with next instance number
            - Return the path that was created in a list
        """
        raise SetValidationError(9000, "Auto Creation for Set not currently supported")

    def _validate_params(self, affected_path, obj_to_update, path_to_set_dict, update_inst_result, param_err_list):
        """Validate the parameters related to the affected path"""
        set_failure_err_list = []

        # Loop through each parameter to validate it
        for param_to_update in obj_to_update.param_setting:
            param_path = affected_path + param_to_update.param
            value_to_set = param_to_update.value
            # TODO: Should validate that it is a writable parameter.
            try:
                curr_value = self._db.get(param_path)
                if curr_value != value_to_set:
                    path_to_set_dict[param_path] = value_to_set
                else:
                    self._logger.info("Ignoring %s: same value as current", param_path)

                update_inst_result.result_param_map[param_to_update.param] = value_to_set
            except agent_db.NoSuchPathError:
                if param_to_update.required:
                    set_failure_err_list.append(param_to_update.param)
                else:
                    param_err = usp.SetResp.ParameterError()
                    param_err.param_path = param_path
                    param_err.param_value = value_to_set
                    param_err.err_code = 9000
                    param_err.err_msg = "Parameter doesn't exist"
                    param_err_list.append(param_err)

        return set_failure_err_list

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
                usp_err_msg = utils.UspErrMsg(req.header.msg_id, to_id, self._id)
                resp = usp_err_msg.generate_error(9000, err_msg)
        else:
            # Unknown agent product class - return an Error
            to_id = req.header.from_id
            err_msg = "Operate Failure: unknown product class - {}".format(product_class)
            usp_err_msg = utils.UspErrMsg(req.header.msg_id, to_id, self._id)
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


class SetValidationError(Exception):
    """A USP Validation Exception for the Set USP Message"""
    def __init__(self, err_code, err_msg):
        """Initialize the Set Validation Error"""
        self._err_msg = err_msg
        self._err_code = err_code
        Exception.__init__(self, "[{}] - {}".format(err_code, err_msg))

    def get_error_code(self):
        """Retrieve the Error Code"""
        return self._err_code

    def get_error_message(self):
        """Retrieve the Error Message"""
        return self._err_msg
