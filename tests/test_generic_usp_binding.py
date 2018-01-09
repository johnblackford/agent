# Copyright (c) 2016 John Blackford
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
#
# File Name: test_generic_usp_binding.py
#
# Description: Unit tests for the generic_usp_binding
#
# Functionality: Test the GenericUspBinding Class
#
"""

import unittest.mock as mock

from agent import generic_usp_binding



def test_empty_pop():
    binding = generic_usp_binding.GenericUspBinding()
    queue_item = binding.pop()

    assert queue_item is None



def test_one_entry():
    payload = "TEST"
    reply_to_addr = "ADDR"
    binding = generic_usp_binding.GenericUspBinding()
    binding.push(payload, reply_to_addr)
    received_payload = binding.pop().get_payload()

    assert payload == received_payload



def test_multiple_entries_seq():
    payload1 = "TEST1"
    reply_to_addr1 = "ADDR1"
    payload2 = "TEST2"
    reply_to_addr2 = "ADDR2"
    payload3 = "TEST3"
    reply_to_addr3 = "ADDR3"
    payload4 = "TEST4"
    reply_to_addr4 = "ADDR4"
    binding = generic_usp_binding.GenericUspBinding()
    binding.push(payload1, reply_to_addr1)
    binding.push(payload2, reply_to_addr2)
    binding.push(payload3, reply_to_addr3)
    binding.push(payload4, reply_to_addr4)
    received_payload1 = binding.pop().get_payload()
    received_payload2 = binding.pop().get_payload()
    received_payload3 = binding.pop().get_payload()
    received_payload4 = binding.pop().get_payload()

    assert payload1 == received_payload1
    assert payload2 == received_payload2
    assert payload3 == received_payload3
    assert payload4 == received_payload4



def test_multiple_entries_not_seq():
    payload1 = "TEST1"
    reply_to_addr1 = "ADDR1"
    payload2 = "TEST2"
    reply_to_addr2 = "ADDR2"
    payload3 = "TEST3"
    reply_to_addr3 = "ADDR3"
    payload4 = "TEST4"
    reply_to_addr4 = "ADDR4"
    binding = generic_usp_binding.GenericUspBinding()
    binding.push(payload1, reply_to_addr1)
    binding.push(payload2, reply_to_addr2)
    received_payload1 = binding.pop().get_payload()
    binding.push(payload3, reply_to_addr3)
    received_payload2 = binding.pop().get_payload()
    received_payload3 = binding.pop().get_payload()
    binding.push(payload4, reply_to_addr4)
    received_payload4 = binding.pop().get_payload()

    assert payload1 == received_payload1
    assert payload2 == received_payload2
    assert payload3 == received_payload3
    assert payload4 == received_payload4



def test_get_msg_found():
    timeout = 15
    payload = "TEST"
    reply_to_addr = "ADDR"
    time_mock = mock.Mock()
    time_mock.return_value = None

    binding = generic_usp_binding.GenericUspBinding(5)
    binding.push(payload, reply_to_addr)

    with mock.patch("time.sleep", time_mock):
        received_payload = binding.get_msg(timeout).get_payload()

    assert payload == received_payload



def test_get_msg_not_found_empty_queue():
    timeout = 15
    time_mock = mock.Mock()
    time_mock.return_value = None

    binding = generic_usp_binding.GenericUspBinding(5)

    with mock.patch("time.sleep", time_mock):
        queue_item = binding.get_msg(timeout)

    assert queue_item is None



def test_get_msg_not_found_not_my_msg():
    timeout = 15
    payload1 = "TEST1"
    reply_to_addr1 = "ADDR1"
    payload2 = "TEST2"
    reply_to_addr2 = "ADDR2"
    payload3 = "TEST3"
    reply_to_addr3 = "ADDR3"
    time_mock = mock.Mock()
    time_mock.return_value = None

    binding = generic_usp_binding.GenericUspBinding(5)
    binding.push(payload1, reply_to_addr1)
    binding.push(payload2, reply_to_addr2)
    binding.push(payload3, reply_to_addr3)

    with mock.patch("time.sleep", time_mock):
        queue_item = binding.get_msg(timeout)
        assert queue_item.get_payload() == payload1
        binding.not_my_msg(queue_item)
        queue_item = binding.get_msg(timeout)
        assert queue_item.get_payload() == payload2
        queue_item = binding.get_msg(timeout)
        assert queue_item.get_payload() == payload3
        queue_item = binding.get_msg(timeout)
        assert queue_item.get_payload() == payload1
