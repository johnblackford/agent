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

import time
import datetime
import unittest.mock as mock

from agent import agent_db


def get_db_file_contents():
    db_contents = """{
        "Device.ControllerNumberOfEntries": "__NUM_ENTRIES__",
        "Device.SubscriptionNumberOfEntries": "__NUM_ENTRIES__",
        "Device.LocalAgent.Manufacturer": "ARRIS",
        "Device.LocalAgent.ManufacturerOUI": "00D09E",
        "Device.LocalAgent.ProductClass": "RPi_Camera",
        "Device.LocalAgent.SerialNumber": "C0000000001",
        "Device.LocalAgent.EndpointID": "usp.00D09E-RPi_Camera-C0000000001",
        "Device.LocalAgent.ModelName": "PoC-USP-Agent-Camera",
        "Device.LocalAgent.HardwareVersion": "RPi2-B",
        "Device.LocalAgent.SoftwareVersion": "0.0.1-alpha",
        "Device.LocalAgent.PeriodicInterval": 300,
        "Device.LocalAgent.ProvisioningCode": "",
        "Device.LocalAgent.SupportedProtocols": "STOMP",
        "Device.LocalAgent.UpTime": "__UPTIME__",
        "Device.LocalAgent.X_ARRIS-COM_IPAddr": "__IPADDR__",
        "Device.Time.Enable" : true,
        "Device.Time.Status" : "Synchronized",
        "Device.Time.NTPServer1" : "ntp1.zzz.com",
        "Device.Time.NTPServer2" : "ntp2.zzz.com",
        "Device.Time.NTPServer3" : "ntp3.zzz.com",
        "Device.Time.NTPServer4" : "",
        "Device.Time.NTPServer5" : "",
        "Device.Time.CurrentLocalTime" : "__CURR_TIME__",
        "Device.Time.LocalTimeZone" : "CST6CDT,M3.2.0/2,M11.1.0",
        "Device.Controller.1.Enable": true,
        "Device.Controller.1.EndpointID": "usp.controller-stomp-johnb",
        "Device.Controller.1.Protocol": "STOMP",
        "Device.Controller.1.CoAP.Host": "",
        "Device.Controller.1.CoAP.Port": 0,
        "Device.Controller.1.STOMP.Host": "stomp.johnblackford.org",
        "Device.Controller.1.STOMP.Port": 61613,
        "Device.Controller.1.STOMP.Username": "jab",
        "Device.Controller.1.STOMP.Password": "johnb23",
        "Device.Controller.2.Enable": true,
        "Device.Controller.2.EndpointID": "usp.controller-coap-johnb",
        "Device.Controller.2.Protocol": "CoAP",
        "Device.Controller.2.CoAP.Host": "localhost",
        "Device.Controller.2.CoAP.Port": 15683,
        "Device.Controller.2.STOMP.Host": "",
        "Device.Controller.2.STOMP.Port": 0,
        "Device.Controller.2.STOMP.Username": "",
        "Device.Controller.2.STOMP.Password": "",
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
        "Device.Subscription.4.Enable": true,
        "Device.Subscription.4.ID": "sub-periodic-coap",
        "Device.Subscription.4.NotifType": "Periodic",
        "Device.Subscription.4.ParamPath": "Device.LocalAgent.",
        "Device.Subscription.4.Controller": "Device.Controller.2.",
        "Device.Subscription.4.TimeToLive": -1,
        "Device.Subscription.4.Persistent": true,
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
        "Device.ControllerNumberOfEntries": "readOnly",
        "Device.SubscriptionNumberOfEntries": "readOnly",
        "Device.LocalAgent.Manufacturer": "readOnly",
        "Device.LocalAgent.ManufacturerOUI": "readOnly",
        "Device.LocalAgent.ProductClass": "readOnly",
        "Device.LocalAgent.SerialNumber": "readOnly",
        "Device.LocalAgent.EndpointID": "readOnly",
        "Device.LocalAgent.ModelName": "readOnly",
        "Device.LocalAgent.HardwareVersion": "readOnly",
        "Device.LocalAgent.SoftwareVersion": "readOnly",
        "Device.LocalAgent.PeriodicInterval": "readWrite",
        "Device.LocalAgent.ProvisioningCode": "readWrite",
        "Device.LocalAgent.SupportedProtocols": "readOnly",
        "Device.LocalAgent.UpTime": "readOnly",
        "Device.LocalAgent.X_ARRIS-COM_IPAddr": "readOnly",
        "Device.Time.Enable" : "readWrite",
        "Device.Time.Status" : "readOnly",
        "Device.Time.NTPServer1" : "readWrite",
        "Device.Time.NTPServer2" : "readWrite",
        "Device.Time.NTPServer3" : "readWrite",
        "Device.Time.NTPServer4" : "readWrite",
        "Device.Time.NTPServer5" : "readWrite",
        "Device.Time.CurrentLocalTime" : "readOnly",
        "Device.Time.LocalTimeZone" : "readWrite",
        "Device.Controller.{i}.Enable": "readWrite",
        "Device.Controller.{i}.EndpointID": "readWrite",
        "Device.Controller.{i}.Protocol": "readWrite",
        "Device.Controller.{i}.CoAP.Host": "readWrite",
        "Device.Controller.{i}.CoAP.Port": "readWrite",
        "Device.Controller.{i}.STOMP.Host": "readWrite",
        "Device.Controller.{i}.STOMP.Port": "readWrite",
        "Device.Controller.{i}.STOMP.Username": "readWrite",
        "Device.Controller.{i}.STOMP.Password": "readWrite",
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


"""
 Tests for find_params
"""


def test_find_param_static_path():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_param_list1 = my_db.find_params("Device.ControllerNumberOfEntries")
        found_param_list2 = my_db.find_params("Device.LocalAgent.SupportedProtocols")

    assert len(found_param_list1) == 1
    assert "Device.ControllerNumberOfEntries" in found_param_list1
    assert len(found_param_list2) == 1
    assert "Device.LocalAgent.SupportedProtocols" in found_param_list2


def test_find_param_static_path_exception():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_params("Device.NoSuchParameter")
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_param_instance_number_addressing():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_param_list1 = my_db.find_params("Device.Controller.1.Enable")
        found_param_list2 = my_db.find_params("Device.Controller.2.STOMP.Username")
        found_param_list3 = my_db.find_params("Device.Services.HomeAutomation.1.Camera.1.Pic.10.URL")

    assert len(found_param_list1) == 1
    assert "Device.Controller.1.Enable" in found_param_list1
    assert len(found_param_list2) == 1
    assert "Device.Controller.2.STOMP.Username" in found_param_list2
    assert len(found_param_list3) == 1
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.10.URL" in found_param_list3


def test_find_param_instance_number_addressing_no_instance():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_param_list1 = my_db.find_params("Device.Services.HomeAutomation.1.Camera.1.Pic.1.URL")

    assert len(found_param_list1) == 0


def test_find_param_wildcard_searching():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_param_list1 = my_db.find_params("Device.Controller.*.Enable")
        found_param_list2 = my_db.find_params("Device.Controller.*.STOMP.Username")
        found_param_list3 = my_db.find_params("Device.Services.HomeAutomation.1.Camera.1.Pic.*.URL")
        found_param_list4 = my_db.find_params("Device.Services.HomeAutomation.1.Camera.*.Pic.*.URL")

    assert len(found_param_list1) == 2
    assert "Device.Controller.1.Enable" in found_param_list1
    assert "Device.Controller.2.Enable" in found_param_list1
    assert len(found_param_list2) == 2
    assert "Device.Controller.1.STOMP.Username" in found_param_list2
    assert "Device.Controller.2.STOMP.Username" in found_param_list2
    assert len(found_param_list3) == 2
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.9.URL" in found_param_list3
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.10.URL" in found_param_list3
    assert len(found_param_list4) == 5
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.9.URL" in found_param_list4
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.10.URL" in found_param_list4
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.10.URL" in found_param_list4
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.90.URL" in found_param_list4
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.100.URL" in found_param_list4


"""
 Tests for find_instances
"""


def test_find_instances_invalid_obj():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_instances("Device.NoSuchObj.")
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_instances_full_path():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_instances("Device.ControllerNumberOfEntries")
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_instances_static_table():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_instances_list1 = my_db.find_instances("Device.Controller.")
        found_instances_list2 = my_db.find_instances("Device.Subscription.")

    assert len(found_instances_list1) == 2
    assert "Device.Controller.1." in found_instances_list1
    assert "Device.Controller.2." in found_instances_list1
    assert len(found_instances_list2) == 4
    assert "Device.Subscription.1." in found_instances_list2
    assert "Device.Subscription.2." in found_instances_list2
    assert "Device.Subscription.3." in found_instances_list2
    assert "Device.Subscription.4." in found_instances_list2


def test_find_instances_instance_number_addressing():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_instances_list1 = my_db.find_instances("Device.Services.HomeAutomation.1.Camera.2.Pic.")

    assert len(found_instances_list1) == 3
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.10." in found_instances_list1
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.90." in found_instances_list1
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.100." in found_instances_list1


def test_find_instances_instance_number_addressing_no_instance():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_instances_list1 = my_db.find_instances("Device.Services.HomeAutomation.1.Camera.3.Pic.")

    assert len(found_instances_list1) == 0


def test_find_instances_wildcard_searching():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_instances_list1 = my_db.find_instances("Device.Services.HomeAutomation.1.Camera.*.Pic.")

    assert len(found_instances_list1) == 5
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.9." in found_instances_list1
    assert "Device.Services.HomeAutomation.1.Camera.1.Pic.10." in found_instances_list1
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.10." in found_instances_list1
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.90." in found_instances_list1
    assert "Device.Services.HomeAutomation.1.Camera.2.Pic.100." in found_instances_list1


"""
 Tests for find_impl_objects
"""


def test_find_impl_objects_invalid_obj():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_impl_objects("Device.NoSuchObj.", False)
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_impl_objects_invalid_obj_next_level():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_impl_objects("Device.NoSuchObj.", True)
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_impl_objects_full_path():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_impl_objects("Device.ControllerNumberOfEntries", False)
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_impl_objects_full_path_next_level():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.find_impl_objects("Device.ControllerNumberOfEntries", True)
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


def test_find_impl_objects_static_table():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.{i}.", False)
        found_objects_list2 = my_db.find_impl_objects("Device.Subscription.", False)
        found_objects_list3 = my_db.find_impl_objects("Device.Services.", False)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 1
    assert "Device.Subscription.{i}." in found_objects_list2
    assert len(found_objects_list3) == 3
#    assert "Device.Services.HomeAutomation." in found_objects_list3
    assert "Device.Services.HomeAutomation.{i}." in found_objects_list3
#    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list3
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}." in found_objects_list3
#    assert "Device.Services.HomeAutomation.{i}.Camera..{i}.Pic." in found_objects_list3
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}." in found_objects_list3


def test_find_impl_objects_static_table_next_level():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.{i}.", True)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.", True)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 1
    assert "Device.Services.HomeAutomation." in found_objects_list2
#    assert "Device.Services.HomeAutomation.{i}." in found_objects_list2


def test_find_impl_objects_instance_number_addressing():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.1.", False)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.HomeAutomation.1.", False)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 2
#    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list2
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}." in found_objects_list2
#    assert "Device.Services.HomeAutomation.{i}.Camera..{i}.Pic." in found_objects_list2
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}." in found_objects_list2


def test_find_impl_objects_instance_number_addressing_next_level():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.2.", True)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.HomeAutomation.1.", True)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 1
    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list2


def test_find_impl_objects_instance_number_addressing_no_instance():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.5.", False)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.HomeAutomation.2.", False)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 2
#    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list2
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}." in found_objects_list2
#    assert "Device.Services.HomeAutomation.{i}.Camera..{i}.Pic." in found_objects_list2
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}." in found_objects_list2


def test_find_impl_objects_instance_number_addressing_no_instance_next_level():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.5.", True)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.HomeAutomation.2.", True)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 1
    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list2


def test_find_impl_objects_wildcard_searching():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.*.", False)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.HomeAutomation.*.", False)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 2
#    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list2
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}." in found_objects_list2
#    assert "Device.Services.HomeAutomation.{i}.Camera..{i}.Pic." in found_objects_list2
    assert "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}." in found_objects_list2


def test_find_impl_objects_wildcard_searching_next_level():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        found_objects_list1 = my_db.find_impl_objects("Device.Controller.*.", True)
        found_objects_list2 = my_db.find_impl_objects("Device.Services.HomeAutomation.*.", True)

    assert len(found_objects_list1) == 2
    assert "Device.Controller.{i}.CoAP." in found_objects_list1
    assert "Device.Controller.{i}.STOMP." in found_objects_list1
    assert len(found_objects_list2) == 1
    assert "Device.Services.HomeAutomation.{i}.Camera." in found_objects_list2


"""
 Tests for get
"""


def test_get_uptime():
    time_mock = start_time_mock = mock.Mock()
    current_time_mock = mock.Mock()

    start_time_mock.return_value = time.mktime(datetime.datetime(2016, 9, 20, 20, 15, 10).timetuple())
    current_time_mock.return_value = time.mktime(datetime.datetime(2016, 9, 21, 1, 16, 15).timetuple())
    time_mock.side_effect = [start_time_mock.return_value, current_time_mock.return_value]

    file_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    file_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", file_mock):
        with mock.patch("time.time", time_mock):
            my_db = agent_db.Database("mock_dm.json", "mock_db.json")
            get_value1 = my_db.get("Device.LocalAgent.UpTime")

    assert get_value1 == 18065


def test_get_num_entries():
    file_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    file_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", file_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        get_value1 = my_db.get("Device.ControllerNumberOfEntries")
        get_value2 = my_db.get("Device.SubscriptionNumberOfEntries")
        get_value3 = my_db.get("Device.Services.HomeAutomation.1.CameraNumberOfEntries")
        get_value4 = my_db.get("Device.Services.HomeAutomation.1.Camera.2.PicNumberOfEntries")

    assert get_value1 == 2
    assert get_value2 == 4
    assert get_value3 == 2
    assert get_value4 == 3


def test_get_ip_addr():
    ip_mock = mock.Mock()
    ip_mock.return_value = "10.99.12.8"

    file_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    file_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", file_mock):
        with mock.patch("agent.utils.IPAddr.get_ip_addr", ip_mock):
            my_db = agent_db.Database("mock_dm.json", "mock_db.json")
            get_value1 = my_db.get("Device.LocalAgent.X_ARRIS-COM_IPAddr")

    assert get_value1 == "10.99.12.8"


def test_get_currrent_local_time():
    time_mock = mock.Mock()
    time_mock.now.return_value = datetime.datetime(2016, 9, 20, 20, 15, 10)

    file_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    file_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", file_mock):
        with mock.patch("datetime.datetime", time_mock):
            my_db = agent_db.Database("mock_dm.json", "mock_db.json")
            get_value1 = my_db.get("Device.Time.CurrentLocalTime")

    assert get_value1 == "2016-09-20T20:15:10-06:00"


def test_get_normal_param():
    file_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    file_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", file_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        get_value1 = my_db.get("Device.LocalAgent.Manufacturer")
        get_value2 = my_db.get("Device.Controller.1.Protocol")
        get_value3 = my_db.get("Device.Subscription.3.ID")
        get_value4 = my_db.get("Device.Services.HomeAutomation.1.Camera.2.MaxNumberOfPics")

    assert get_value1 == "ARRIS"
    assert get_value2 == "STOMP"
    assert get_value3 == "sub-boot-coap"
    assert get_value4 == 30


def test_get_no_such_path():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        try:
            my_db.get("Device.NoSuchParam")
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


"""
 Tests for update
   NOTE: Mocking the _save method
"""


def test_update_param():
    file_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    file_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", file_mock):
        with mock.patch.object(agent_db.Database, '_save') as save_mock:
            my_db = agent_db.Database("mock_dm.json", "mock_db.json")
            my_db.update("Device.LocalAgent.PeriodicInterval", 60)

    save_mock.assert_called_once_with()


def test_update_no_such_path():
    my_mock = dm_mock = mock.mock_open(read_data=get_dm_file_contents())
    db_mock = mock.mock_open(read_data=get_db_file_contents())
    my_mock.side_effect = [dm_mock.return_value, db_mock.return_value]

    with mock.patch("builtins.open", my_mock):
        my_db = agent_db.Database("mock_dm.json", "mock_db.json")
        my_db._save = mock.MagicMock()

        try:
            my_db.update("Device.NoSuchParam", "ZZZ")
            assert True, "NoSuchPathError Excepted"
        except agent_db.NoSuchPathError:
            pass


"""
 Tests for insert
   NOTE: Mocking the _save method
"""


"""
 Tests for delete
   NOTE: Mocking the _save method
"""
