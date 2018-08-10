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
import prometheus_client

from agent import utils
from agent import agent_db
from agent import usp_msg_pb2 as usp_msg
from agent import usp_record_pb2 as usp_record


TAKE_PICTURE_CAMERA_OP = "Device.Services.HomeAutomation.1.Camera.1.TakePicture()"

# pylint: disable-msg=no-value-for-parameter
NUM_GET_MSGS_METRIC = \
    prometheus_client.Counter("number_of_usp_get_msgs",
                              "Number of USP Get Messages")
# pylint: disable-msg=no-value-for-parameter
NUM_SET_MSGS_METRIC = \
    prometheus_client.Counter("number_of_usp_set_msgs",
                              "Number of USP Set Messages")
# pylint: disable-msg=no-value-for-parameter
NUM_OPERATE_MSGS_METRIC = \
    prometheus_client.Counter("number_of_usp_operate_msgs",
                              "Number of USP Operate Messages")
# pylint: disable-msg=no-value-for-parameter
NUM_UNKNOWN_MSGS_METRIC = \
    prometheus_client.Counter("number_of_usp_unknown_msgs",
                              "Number of Unknown USP Messages")


class UspRequestHandler(object):
    """A USP Message Handler: to be used by a USP Agent"""
    def __init__(self, endpoint_id, agent_database, service_map=None, debug=False):
        """Initialize the USP Request Handler"""
        self._debug = debug
        self._id = endpoint_id
        self._db = agent_database
        self._service_map = service_map
        self._logger = logging.getLogger(self.__class__.__name__)

    def handle_request(self, msg_payload):
        """Handle a Request/Response interaction"""
        req_record = self._handle_usp_record(msg_payload)

        try:
            # Validate the payload before processing it
            self._validate_usp_record_request(req_record)
            req_msg = self._handle_usp_msg(req_record)
            self._validate_usp_msg_request(req_msg)
            self._logger.info("Received a [%s] Request",
                              req_msg.body.request.WhichOneof("req_type"))

            resp_msg, resp_record = self._process_request(req_record, req_msg)
            if self._debug:
                print("Outgoing Response:\n{}".format(resp_msg))
        except ProtocolValidationError as err:
            err_msg = "USP Message validation failed: {}".format(err)
            self._logger.error("%s", err_msg)
            raise ProtocolViolationError(err_msg)

        return req_msg, req_record, resp_msg, resp_record.SerializeToString()

    def _handle_usp_record(self, msg_payload):
        """Deserialize the USP Record in the Incoming Request"""
        req_as_record = usp_record.Record()

        # De-Serialize the payload into a USP Record
        req_as_record.ParseFromString(msg_payload)
        self._logger.debug("Incoming payload parsed as a USP Record via Protocol Buffers")

        if self._debug:
            debug_msg = "Incoming USP Record:\n{}".format(req_as_record)
            self._logger.debug("%s", debug_msg)

        return req_as_record

    def _validate_usp_record_request(self, req_as_record):
        """Validate the USP Record from the Incoming Request"""
        if not req_as_record.IsInitialized():
            raise ProtocolValidationError("USP Record missing Required Fields")

        if len(req_as_record.version) <= 0:
            raise ProtocolValidationError("USP Record missing version")

        if len(req_as_record.to_id) <= 0:
            raise ProtocolValidationError("USP Record missing to_id")

        if req_as_record.to_id != self._id:
            raise ProtocolValidationError("USP Record has incorrect to_id")

        if len(req_as_record.from_id) <= 0:
            raise ProtocolValidationError("Header missing from_id")

        if not req_as_record.payload_security == usp_record.Record.PLAINTEXT:
            raise ProtocolValidationError("USP Record has unsupported Payload Security")

        if not req_as_record.WhichOneof("record_type") == "no_session_context":
            raise ProtocolValidationError("USP Record has an unsupported Record Type")

        self._logger.info("Incoming USP Record passed validation")

    def _handle_usp_msg(self, req_as_record):
        """Deserialize the USP Record in the Incoming Request"""
        req_as_msg = usp_msg.Msg()

        # De-Serialize the payload into a USP Record
        req_as_msg.ParseFromString(req_as_record.no_session_context.payload)
        self._logger.debug("Incoming payload parsed as a USP Message via Protocol Buffers")

        if self._debug:
            debug_msg = "Incoming USP Message:\n{}".format(req_as_msg)
            self._logger.debug("%s", debug_msg)

        return req_as_msg

    def _validate_usp_msg_request(self, req_as_msg):
        """Validate the USP Message from the Incoming USP Record"""
        if not req_as_msg.IsInitialized():
            raise ProtocolValidationError("USP Message missing Required Fields")

        if len(req_as_msg.header.msg_id) <= 0:
            raise ProtocolValidationError("USP Message Header missing msg_id")

        if not req_as_msg.body.WhichOneof("msg_body") == "request":
            raise ProtocolValidationError("USP Message Body doesn't contain a Request element")

        self._logger.info("Incoming USP Message passed validation")

    def _process_request(self, req_as_record, req_as_msg):
        """Processing the incoming Message and return a Response"""
        to_id = req_as_record.from_id
        resp_record = usp_record.Record()
        err_msg = "Message Failure: Request body does not match Header msg_type"
        usp_err_msg = utils.UspErrMsg(req_as_msg.header.msg_id)
        resp_msg = usp_err_msg.generate_error(9000, err_msg)

        if req_as_msg.header.msg_type == usp_msg.Header.GET:
            # Validate that the Request body matches the Header's msg_type
            if req_as_msg.body.request.WhichOneof("req_type") == "get":
                NUM_GET_MSGS_METRIC.inc()
                resp_msg = self._process_get(req_as_msg)
        elif req_as_msg.header.msg_type == usp_msg.Header.SET:
            # Validate that the Request body matches the Header's msg_type
            if req_as_msg.body.request.WhichOneof("req_type") == "set":
                NUM_SET_MSGS_METRIC.inc()
                resp_msg = self._process_set(req_as_msg)
        elif req_as_msg.header.msg_type == usp_msg.Header.OPERATE:
            # Validate that the Request body matches the Header's msg_type
            if req_as_msg.body.request.WhichOneof("req_type") == "operate":
                NUM_OPERATE_MSGS_METRIC.inc()
                resp_msg = self._process_operation(req_as_msg)
        else:
            err_msg = "Invalid USP Message: unknown command"
            resp_msg = usp_err_msg.generate_error(9000, err_msg)
            NUM_UNKNOWN_MSGS_METRIC.inc()

        # Wrap the USP Message response into a USP Record
        resp_record.version = "1.0"
        resp_record.to_id = to_id
        resp_record.from_id = self._id
        resp_record.payload_security = usp_record.Record.PLAINTEXT
        resp_record.no_session_context.payload = resp_msg.SerializeToString()

        return resp_msg, resp_record

    def _process_get(self, req_msg):
        """Process an incoming Get and generate a GetResp"""
        resp_msg = usp_msg.Msg()
        path_result_list = []
        self._logger.info("Processing a Get Request...")

        # Populate the Response's Header information
        resp_msg.header.msg_id = req_msg.header.msg_id
        resp_msg.header.msg_type = usp_msg.Header.GET_RESP

        # Process the Parameter Paths in the Get Request
        for req_path in req_msg.body.request.get.param_paths:
            path_result = usp_msg.GetResp.RequestedPathResult()
            path_result.requested_path = req_path

            try:
                resolved_path_list = []
                partial_path, param_name = self._split_path(req_path)
                self._logger.debug("Split into [%s] and [%s]", partial_path, param_name)
                affected_path_list = self._get_affected_paths_for_get(partial_path)

                for affected_path in affected_path_list:
                    self._logger.debug("Requested Path [%s] resolved to: %s", req_path, affected_path)
                    resolved_path_result = usp_msg.GetResp.ResolvedPathResult()
                    resolved_path_result.resolved_path = affected_path

                    if param_name is None:
                        items = self._db.find_params(affected_path)

                        for item in items:
                            param_path = self._diff_paths(affected_path, item)
                            resolved_path_result.result_params[param_path] = str(self._db.get(item))
                    else:
                        param = affected_path + param_name
                        resolved_path_result.result_params[param_name] = str(self._db.get(param))

                    resolved_path_list.append(resolved_path_result)

                path_result.resolved_path_results.extend(resolved_path_list)
            except agent_db.NoSuchPathError:
                self._logger.warning("Invalid Path encountered: %s", req_path)
                path_result.err_code = 11002
                path_result.err_msg = "Invalid Path: " + req_path + " is not a part of the supported data model"

            path_result_list.append(path_result)

        resp_msg.body.response.get_resp.req_path_results.extend(path_result_list)

        return resp_msg

    def _process_set(self, req_msg):
        """Process an incoming Set and generate a SetResp"""
        resp_msg = usp_msg.Msg()
        path_to_set_dict = {}
        update_obj_result_list = []
        set_failure_param_err_list = []
        self._logger.info("Processing a Set Request...")

        # Populate the Response's Header information
        resp_msg.header.msg_id = req_msg.header.msg_id
        resp_msg.header.msg_type = usp_msg.Header.SET_RESP

        # Validate the Set Request and populate the dictionaries and lists appropriately
        self._validate_set(req_msg, path_to_set_dict, update_obj_result_list, set_failure_param_err_list)

        # Finished with all validation, process the errors or make the updates
        if len(set_failure_param_err_list) > 0:
            usp_err_msg = utils.UspErrMsg(req_msg.header.msg_id)
            err_msg = "Invalid Path Found, Allow Partial Updates = False :: Fail the entire Set"
            resp = usp_err_msg.generate_error(9000, err_msg)
            resp.body.error.param_errs.extend(set_failure_param_err_list)
        else:
            # Process the Updates against the database
            for param_path in path_to_set_dict:
                self._db.update(param_path, path_to_set_dict[param_path])

            resp_msg.body.response.set_resp.updated_obj_results.extend(update_obj_result_list)

        return resp_msg

    def _validate_set(self, req_msg, path_to_set_dict, update_obj_result_list, set_failure_param_err_list):
        """Validate the Set Request"""
        # Retrieve the all_partial flag from the request
        allow_partial_updates = req_msg.body.request.set.allow_partial

        # Loop through each UpdateObject
        for obj_to_update in req_msg.body.request.set.update_objs:
            update_inst_result_list = []
            obj_path_set_failure_err_dict = {}
            obj_path_to_update = obj_to_update.obj_path

            try:
                affected_path_list = self._get_affected_paths_for_set(obj_path_to_update)

                # For each Affected Path, update the Parameter Settings
                for affected_path in affected_path_list:
                    set_failure_err_list, update_inst_result = \
                        self._validate_set_params(affected_path, obj_to_update, path_to_set_dict)

                    if len(set_failure_err_list) > 0:
                        obj_path_set_failure_err_dict[affected_path] = set_failure_err_list

                    update_inst_result_list.append(update_inst_result)

                if len(obj_path_set_failure_err_dict) == 0:
                    # If there were no Set Failure errors for the obj_to_update, oper_success
                    update_obj_result = usp_msg.SetResp.UpdatedObjectResult()
                    update_obj_result.requested_path = obj_path_to_update
                    update_obj_result.oper_status.oper_success.updated_inst_results.extend(update_inst_result_list)
                    update_obj_result_list.append(update_obj_result)
                else:
                    self._handle_set_param_errors(obj_path_to_update, allow_partial_updates,
                                                  obj_path_set_failure_err_dict, update_obj_result_list,
                                                  set_failure_param_err_list)
            except SetValidationError as sv_err:
                self._handle_set_validation_err(obj_path_to_update, allow_partial_updates,
                                                sv_err, update_obj_result_list, set_failure_param_err_list)

    def _validate_set_params(self, affected_path, obj_to_update, path_to_set_dict):
        """Validate the parameters related to the affected path"""
        param_err_list = []
        set_failure_err_list = []
        update_inst_result = usp_msg.SetResp.UpdatedInstanceResult()
        update_inst_result.affected_path = affected_path

        # Loop through each parameter to validate it
        for param_to_update in obj_to_update.param_settings:
            err_msg = ""
            param_failure = False
            param_path = affected_path + param_to_update.param
            value_to_set = param_to_update.value

            try:
                if self._db.is_param_writable(param_path):
                    # TODO: Also need to not allow sets against unmutable parameters and objects
                    curr_value = self._db.get(param_path)
                    if curr_value != value_to_set:
                        path_to_set_dict[param_path] = value_to_set
                    else:
                        self._logger.info("Ignoring %s: same value as current", param_path)

                    update_inst_result.updated_params[param_to_update.param] = value_to_set
                else:
                    param_failure = True
                    err_msg = "Parameter is not writable"
            except agent_db.NoSuchPathError:
                param_failure = True
                err_msg = "Parameter does not exist"

            if param_failure:
                param_err = usp_msg.SetResp.ParameterError()
                param_err.param = param_to_update.param
                param_err.err_code = 9000
                param_err.err_msg = err_msg

                if param_to_update.required:
                    set_failure_err_list.append(param_err)
                else:
                    param_err_list.append(param_err)

        update_inst_result.param_errs.extend(param_err_list)

        return set_failure_err_list, update_inst_result

    def _handle_set_param_errors(self, obj_path_to_update, allow_partial_updates, obj_path_set_failure_err_dict,
                                 update_obj_result_list, set_failure_param_err_list):
        """Handle any errors generated from validating the individual parameters"""
        # If there were Set Failure errors for the obj_to_update
        if allow_partial_updates:
            # Set Failures are handled via oper_failure on the SetResp
            failure_list = []
            param_err_list = []
            err_msg = "Failed to Set Required Parameters"

            update_obj_result = usp_msg.SetResp.UpdatedObjectResult()
            update_obj_result.requested_path = obj_path_to_update
            update_obj_result.oper_status.oper_failure.err_code = 9000
            update_obj_result.oper_status.oper_failure.err_msg = err_msg

            for affected_path in obj_path_set_failure_err_dict:
                failure = usp_msg.SetResp.UpdatedInstanceFailure()
                failure.affected_path = affected_path

                for param_err in obj_path_set_failure_err_dict[affected_path]:
                    param_err_list.append(param_err)

                failure.param_errs.extend(param_err_list)
                failure_list.append(failure)

            update_obj_result.oper_status.oper_failure.updated_inst_failures.extend(failure_list)
            update_obj_result_list.append(update_obj_result)
        else:
            # Set Failures are handled via ParamError on an Error message
            for affected_path in obj_path_set_failure_err_dict:
                for param_err in obj_path_set_failure_err_dict[affected_path]:
                    set_failure_param_err = usp_msg.Error.ParamError()
                    set_failure_param_err.param_path = affected_path + param_err.param
                    set_failure_param_err.err_code = param_err.err_code
                    set_failure_param_err.err_msg = param_err.err_msg
                    set_failure_param_err_list.append(set_failure_param_err)

    def _handle_set_validation_err(self, obj_path_to_update, allow_partial_updates, sv_err,
                                   update_obj_result_list, set_failure_param_err_list):
        """Handle any errors generated from validating the object path"""
        if allow_partial_updates:
            # Invalid Path Found, Allow Partial Updates = True :: Fail this one object path
            update_obj_result = usp_msg.SetResp.UpdatedObjectResult()
            update_obj_result.requested_path = obj_path_to_update
            update_obj_result.oper_status.oper_failure.err_code = sv_err.get_error_code()
            update_obj_result.oper_status.oper_failure.err_msg = sv_err.get_error_message()
            update_obj_result_list.append(update_obj_result)
        else:
            # Invalid Path Found, Allow Partial Updates = False :: Fail the entire Set
            set_failure_param_err = usp_msg.Error.ParamError()
            set_failure_param_err.param_path = obj_path_to_update
            set_failure_param_err.err_code = sv_err.get_error_code()
            set_failure_param_err.err_msg = sv_err.get_error_message()
            set_failure_param_err_list.append(set_failure_param_err)

    def _process_operation(self, req_msg):
        """Process an incoming Operate and generate a OperateResp"""
        resp_msg = usp_msg.Msg()
        op_result_list = []
        command = req_msg.body.request.operate.command
        product_class = self._db.get("Device.DeviceInfo.ProductClass")
        self._logger.info("Processing an Operate Request...")

        # TODO: This is hard-coded for the Camera, but needs to be dynamic

        # Populate the Response's Header information
        resp_msg.header.msg_id = req_msg.header.msg_id
        resp_msg.header.msg_type = usp_msg.Header.OPERATE_RESP

        if product_class == "RPi_Camera" or product_class == "RPiZero_Camera":
            # Validate that the Operate.command is supported
            if command == TAKE_PICTURE_CAMERA_OP:
                op_result = usp_msg.OperateResp.OperationResult()
                out_arg_map = op_result.req_output_args.output_args
                camera = self._service_map[product_class]
                param_map = camera.take_picture()
                for param in param_map:
                    out_arg_map[param] = param_map[param]

                op_result_list.append(op_result)
                resp_msg.body.response.operate_resp.operation_results.extend(op_result_list)
            else:
                # Invalid Command - return an Error
                err_msg = "Operate Failure: invalid command - {}".format(command)
                usp_err_msg = utils.UspErrMsg(req_msg.header.msg_id)
                resp_msg = usp_err_msg.generate_error(9000, err_msg)
        else:
            # Unknown agent product class - return an Error
            err_msg = "Operate Failure: unknown product class - {}".format(product_class)
            usp_err_msg = utils.UspErrMsg(req_msg.header.msg_id)
            resp_msg = usp_err_msg.generate_error(9000, err_msg)

        return resp_msg

    def _split_path(self, path):
        """Split an incoming path into its partial path and parameter name
            - Return None for param_name if a partial path was provided"""
        param_name = None

        if path.endswith("."):
            partial_path = path
        else:
            path_parts = path.split(".")
            partial_path_len = len(path_parts) - 1
            partial_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
            param_name = path_parts[partial_path_len]

        return partial_path, param_name

    def _diff_paths(self, negative_path, full_path):
        """Construct a path that removes the negative_path portion from the full_path portion"""
        index = 0
        return_path = ""
        negative_path_parts = negative_path.split(".")
        full_path_parts = full_path.split(".")
        num_full_path_parts = len(full_path_parts)

        for negative_path_part in negative_path_parts:
            if negative_path_part == full_path_parts[index]:
                index += 1
            else:
                break

        while index < num_full_path_parts:
            return_path += full_path_parts[index]
            if (index + 1) < num_full_path_parts:
                return_path += "."
            index += 1

        return return_path

    def _get_affected_paths_for_get(self, partial_path):
        """
          Retrieve the affected paths based on the incoming obj_path:
            - For Get Messages, we only want to validate that it is a supported path, even if instances are not there
        """
        affected_path_list = self._db.find_objects(partial_path)
        num_affected_path_list = len(affected_path_list)
        self._logger.info("Found [%s] Affected Paths for %s", str(num_affected_path_list), partial_path)

        return affected_path_list

    def _get_affected_paths_for_set(self, partial_path):
        """
          Retrieve the affected paths based on the incoming obj_path:
            - For Set Messages, we only want existing Paths (including general validation and that it is supported)
        """
        is_static_path = self._is_partial_path_static(partial_path)
        is_search_path = self._is_partial_path_searching(partial_path)

        try:
            affected_path_list = self._db.find_objects(partial_path)

            if len(affected_path_list) == 0:
                if is_search_path or is_static_path:
                    pass
                else:
                    err_code = 9000
                    err_msg = "Non-existent obj_path encountered - {}".format(partial_path)
                    raise SetValidationError(err_code, err_msg)
        except agent_db.NoSuchPathError:
            err_code = 9000
            err_msg = "Invalid obj_path encountered - {}".format(partial_path)
            raise SetValidationError(err_code, err_msg)

        return affected_path_list

    def _is_partial_path_static(self, partial_path):
        """
          Check to see that the partial_path doesn't contain:
            - Instance Number based addressing elements
            - FUTURE: Unique Key based addressing elements
            - wildcard-based searching elements
            - FUTURE: expression-based searching elements
        """
        if not self._is_partial_path_searching(partial_path):
            pattern = re.compile(r'\.[0-9]+\.')
            if pattern.search(partial_path) is None:
                return True

        return False

    def _is_partial_path_searching(self, partial_path):
        """
          Check to see if the partial_path contains:
            - wildcard-based searching elements
            - FUTURE: expression-based searching elements
        """
        return ".*." in partial_path


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
