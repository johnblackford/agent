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

def test_split_path_wildcard_path():
    endpoint_id = "ENDPOINT-ID"
    mock_db = mock.create_autospec(agent_db.Database)
    req_handler = request_handler.UspRequestHandler(endpoint_id, mock_db)
    path = "Device.LocalAgent.Controller.*.MTP.*."

    partial_path, param_name = req_handler._split_path(path)

    assert partial_path == "Device.LocalAgent.Controller.*.MTP.*.", "Partial Path Failure"
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


"""
 Tests for _get_affected_paths_for_get
"""

def get_db_file_contents():
    db_contents = """{
        "Device.SubscriptionNumberOfEntries": "__NUM_ENTRIES__",
        "Device.Subscription.1.Enable": true,
        "Device.Subscription.1.ID": "sub-boot-stomp",
        "Device.Subscription.1.NotifType": "Boot",
        "Device.Subscription.1.ParamPath": "Device.LocalAgent.",
        "Device.Subscription.1.Controller": "Device.Controller.1.",
        "Device.Subscription.1.TimeToLive": -1,
        "Device.Subscription.1.Persistent": true,
        "Device.Subscription.2.Enable": true,
        "Device.Subscription.2.ID": "sub-periodic-stomp",
        "Device.Subscription.2.NotifType": "Periodic",
        "Device.Subscription.2.ParamPath": "Device.LocalAgent.",
        "Device.Subscription.2.Controller": "Device.Controller.1.",
        "Device.Subscription.2.TimeToLive": -1,
        "Device.Subscription.2.Persistent": true,
        "Device.Subscription.3.Enable": true,
        "Device.Subscription.3.ID": "sub-boot-coap",
        "Device.Subscription.3.NotifType": "Boot",
        "Device.Subscription.3.ParamPath": "Device.LocalAgent.",
        "Device.Subscription.3.Controller": "Device.Controller.2.",
        "Device.Subscription.3.TimeToLive": -1,
        "Device.Subscription.3.Persistent": true,
        "Device.Services.HomeAutomationNumberOfEntries": "__NUM_ENTRIES__",
        "Device.Services.HomeAutomation.1.CameraNumberOfEntries": "__NUM_ENTRIES__",
        "Device.Services.HomeAutomation.1.Camera.1.MaxNumberOfPics": 30,
        "Device.Services.HomeAutomation.1.Camera.1.PicNumberOfEntries": "__NUM_ENTRIES__",
        "Device.Services.HomeAutomation.1.Camera.1.Pic.__NextInstNum__": 11,
        "Device.Services.HomeAutomation.1.Camera.1.Pic.9.URL": "http://localhost:8080/pic1.png",
        "Device.Services.HomeAutomation.1.Camera.1.Pic.10.URL": "http://localhost:8080/pic2.png",
        "Device.Services.HomeAutomation.1.Camera.2.MaxNumberOfPics": 30,
        "Device.Services.HomeAutomation.1.Camera.2.PicNumberOfEntries": "__NUM_ENTRIES__",
        "Device.Services.HomeAutomation.1.Camera.2.Pic.__NextInstNum__": 11,
        "Device.Services.HomeAutomation.1.Camera.2.Pic.10.URL": "http://localhost:8080/pic5.png",
        "Device.Services.HomeAutomation.1.Camera.2.Pic.90.URL": "http://localhost:8080/pic9.png",
        "Device.Services.HomeAutomation.1.Camera.2.Pic.100.URL": "http://localhost:8080/pic20.png"
    }"""
    return db_contents


def get_dm_file_contents():
    dm_contents = """{
        "Device.SubscriptionNumberOfEntries": "readOnly",
        "Device.Subscription.{i}.Enable": "readWrite",
        "Device.Subscription.{i}.ID": "readWrite",
        "Device.Subscription.{i}.NotifType": "readWrite",
        "Device.Subscription.{i}.ParamPath": "readWrite",
        "Device.Subscription.{i}.Controller": "readWrite",
        "Device.Subscription.{i}.TimeToLive": "readWrite",
        "Device.Subscription.{i}.Persistent": "readWrite",
        "Device.Services.HomeAutomationNumberOfEntries": "readOnly",
        "Device.Services.HomeAutomation.{i}.CameraNumberOfEntries": "readOnly",
        "Device.Services.HomeAutomation.{i}.Camera.{i}.TakePicture()": "readWrite",
        "Device.Services.HomeAutomation.{i}.Camera.{i}.MaxNumberOfPics": "readWrite",
        "Device.Services.HomeAutomation.{i}.Camera.{i}.PicNumberOfEntries": "readOnly",
        "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}.URL": "readOnly"
    }"""
    return dm_contents

def test_get_affected_paths_for_get_partial_path():
    endpoint_id = "ENDPOINT-ID"
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]
    partial_path = "Device.Subscription."

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json", "intf")
        req_handler = request_handler.UspRequestHandler(endpoint_id, my_db)
        affected_path_list = req_handler._get_affected_paths_for_get(partial_path)

    assert len(affected_path_list) == 1, "expecting 1, found " + str(len(affected_path_list))
    assert affected_path_list[0] == "Device.Subscription."

def test_get_affected_paths_for_get_wildcard_path():
    endpoint_id = "ENDPOINT-ID"
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]
    partial_path = "Device.Subscription.*."

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json", "intf")
        req_handler = request_handler.UspRequestHandler(endpoint_id, my_db)
        affected_path_list = req_handler._get_affected_paths_for_get(partial_path)

    assert len(affected_path_list) == 3, "expecting 3, found " + str(len(affected_path_list))

def test_get_affected_paths_for_get_two_layers():
    endpoint_id = "ENDPOINT-ID"
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]
    partial_path = "Device.Services.HomeAutomation.*.Camera.*.Pic."

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json", "intf")
        req_handler = request_handler.UspRequestHandler(endpoint_id, my_db)
        affected_path_list = req_handler._get_affected_paths_for_get(partial_path)

    assert len(affected_path_list) == 2, "expecting 2, found " + str(len(affected_path_list))

def test_get_affected_paths_for_get_three_layers():
    endpoint_id = "ENDPOINT-ID"
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]
    partial_path = "Device.Services.HomeAutomation.*.Camera.*.Pic.*."

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json", "intf")
        req_handler = request_handler.UspRequestHandler(endpoint_id, my_db)
        affected_path_list = req_handler._get_affected_paths_for_get(partial_path)

    assert len(affected_path_list) == 5, "expecting 5, found " + str(len(affected_path_list))
