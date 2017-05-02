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
# File Name: test_path_helper.py
#
# Description: Unit tests for the PathHelper utils module
#
# Functionality: Test the PathHelper Class
#
"""


from agent import utils


def test_object_path():
    path = "Device.Object.Parameter"
    path_parts = path.split(".")

    partial_path_len = len(path_parts) - 1
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object."

    partial_path_len = 2
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object."


def test_table_path():
    path = "Device.Object.Table.1.Parameter"
    path_parts = path.split(".")

    partial_path_len = len(path_parts) - 1
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object.Table.1."

    partial_path_len = 4
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object.Table.1."

    partial_path_len = 3
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object.Table."


def test_partial_path():
    path = "Device.Object.Table.1."
    path_parts = path.split(".")

    partial_path_len = len(path_parts) - 1
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object.Table.1."

    partial_path_len = len(path_parts) - 2
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object.Table."


def test_multiple_levels():
    path = "Device.Object.Table.1.Parameter"
    path_parts = path.split(".")

    partial_path_len = 2
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == "Device.Object."


def test_level_zero():
    path = "Device.Object.Table.1.Parameter"
    path_parts = path.split(".")

    partial_path_len = 0
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == ""


def test_level_too_long():
    path = "Device.Object.Table.1.Parameter"
    path_parts = path.split(".")

    partial_path_len = len(path_parts)
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == path

    partial_path_len = 5
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == path

    partial_path_len = 6
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == path

    partial_path_len = 1005
    built_path = utils.PathHelper.build_path_from_parts(path_parts, partial_path_len)
    assert built_path == path


def test_error_path_instead_of_path_parts():
    path = "Device.Object.Table.1.Parameter"
    built_path = utils.PathHelper.build_path_from_parts(path, 1)
    assert built_path == ""
