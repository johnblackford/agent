#! /usr/bin/env python3

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

# File Name: test_config_mgr.py
#
# Description: Unit tests for the ConfigMgr Class
#
"""

import unittest.mock as mock

from agent import utils


def test_item_in_config_file():
    mock_cfg_file = "{\"key1\" : \"value1\", \"key2\" : \"value2\"}"
    cfg_file_defaults = {"key1": "defaultValue1",
                         "key2": "defaultValue2",
                         "key3": "defaultValue3"}

    with mock.patch("builtins.open",
                    mock.mock_open(read_data=mock_cfg_file)) as my_mock:
        cfg_mgr = utils.ConfigMgr("mock.cfg", cfg_file_defaults)
        value1 = cfg_mgr.get_cfg_item("key1")
        value2 = cfg_mgr.get_cfg_item("key2")

    my_mock.assert_called_once_with("mock.cfg", "r")
    assert value1 == "value1"
    assert value2 == "value2"


def test_item_not_in_config_file_with_default():
    mock_cfg_file = "{\"key0\" : \"value0\"}"
    cfg_file_defaults = {"key1": "defaultValue1",
                         "key2": "defaultValue2"}

    with mock.patch("builtins.open",
                    mock.mock_open(read_data=mock_cfg_file)) as my_mock:
        cfg_mgr = utils.ConfigMgr("mock.cfg", cfg_file_defaults)
        value1 = cfg_mgr.get_cfg_item("key1")
        value2 = cfg_mgr.get_cfg_item("key2")

    my_mock.assert_called_once_with("mock.cfg", "r")
    assert value1 == "defaultValue1"
    assert value2 == "defaultValue2"


def test_empty_file():
    mock_cfg_file = ""
    cfg_file_defaults = {"key1": "defaultValue1",
                         "key2": "defaultValue2"}

    with mock.patch("builtins.open",
                    mock.mock_open(read_data=mock_cfg_file)) as my_mock:
        cfg_mgr = utils.ConfigMgr("mock.cfg", cfg_file_defaults)
        value1 = cfg_mgr.get_cfg_item("key1")
        value2 = cfg_mgr.get_cfg_item("key2")

    my_mock.assert_called_once_with("mock.cfg", "r")
    assert value1 == "defaultValue1"
    assert value2 == "defaultValue2"


def test_no_file():
    cfg_file_defaults = {"key1": "defaultValue1",
                         "key2": "defaultValue2"}

    cfg_mgr = utils.ConfigMgr("config_file_that_doesnt_exist.cfg", cfg_file_defaults)
    value1 = cfg_mgr.get_cfg_item("key1")
    value2 = cfg_mgr.get_cfg_item("key2")

    assert value1 == "defaultValue1"
    assert value2 == "defaultValue2"


def test_item_not_in_config_file_no_default():
    mock_cfg_file = "{\"key1\" : \"value1\"}"
    cfg_file_defaults = {"key2": "defaultValue2"}

    with mock.patch("builtins.open",
                    mock.mock_open(read_data=mock_cfg_file)) as my_mock:
        cfg_mgr = utils.ConfigMgr("mock.cfg", cfg_file_defaults)
        try:
            value = cfg_mgr.get_cfg_item("key3")
            assert value == "Expected a config_mgr.MissingConfigError to be raised"
        except utils.MissingConfigError:
            pass
