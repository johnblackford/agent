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

# File Name: test_agent_db.py
#
# Description: Unit tests for the Database Class
#
"""

import unittest.mock as mock

from agent import agent_db
from agent import request_handler


"""
 Tests for _is_set_path_static
"""


def test_is_set_path_static():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)

    assert req_handler._is_partial_path_static("Device.LocalAgent."), "Static Path Failure"
    assert not req_handler._is_partial_path_static("Device.Controller.1."), "Instance Number Addressing Path Failure"
    assert not req_handler._is_partial_path_static("Device.Controller.*."), "Wildcard-based Searching Path Failure"


"""
 Tests for _is_set_path_searching
"""


def test_is_set_path_searching():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)

    assert not req_handler._is_partial_path_searching("Device.LocalAgent."), "Static Path Failure"
    assert not req_handler._is_partial_path_searching("Device.Controller.1."), "Instance Number Addressing Path Failure"
    assert req_handler._is_partial_path_searching("Device.Controller.*."), "Wildcard-based Searching Path Failure"


"""
 Tests for _split_path
"""


def test_split_path_full_path():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)
    path = "Device.LocalAgent.Controller.1.MTP.1.Protocol"

    partial_path, param_name = req_handler._split_path(path)

    assert partial_path == "Device.LocalAgent.Controller.1.MTP.1.", "Partial Path Failure"
    assert param_name == "Protocol", "Parameter Name Failure"

def test_split_path_partial_path():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)
    path = "Device.LocalAgent.Controller.1.MTP.1."

    partial_path, param_name = req_handler._split_path(path)

    assert partial_path == "Device.LocalAgent.Controller.1.MTP.1.", "Partial Path Failure"
    assert param_name is None, "Parameter Name Failure, should be None"


"""
 Tests for _diff_paths
"""


def test_diff_paths_partial_path_req():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)
    req_path = "Device.LocalAgent.Controller."
    param_path = "Device.LocalAgent.Controller.1.EndpointID"

    diff_path = req_handler._diff_paths(req_path, param_path)

    assert diff_path == "1.EndpointID"

def test_diff_paths_wildcard_path_req():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)
    req_path = "Device.LocalAgent.Controller.*."
    param_path = "Device.LocalAgent.Controller.1.EndpointID"

    diff_path = req_handler._diff_paths(req_path, param_path)

    assert diff_path == "1.EndpointID"

def test_diff_paths_multiple_wildcard_path_req():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)
    req_path = "Device.LocalAgent.Controller.*.MTP.*."
    param_path = "Device.LocalAgent.Controller.1.MTP.2.Protocol"

    diff_path = req_handler._diff_paths(req_path, param_path)

    assert diff_path == "1.MTP.2.Protocol"
