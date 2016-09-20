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

# File Name: agent_db.py
#
# Description: Rudimentary Agent Database
#
# Functionality:
#  - Dictionary as a database (key=full parameter path, value=parameter value)
#  - The database is initialized from a JSON formatted file
#  - Get command for full parameter path
#  - Update command for full parameter path
#  - Insert command for tables
#  - Delete command for tables
#  - Find commands for wild-carded or partial parameter paths (returns full parameter paths)
#  --- find_params: find parameter paths
#  --- find_instances: find multi-object instance partial paths
#  --- find_impl_objects: find implemented object partial paths
#  - Save command (saves the contents of the database back to a file)
#
"""


import re
import json
import time
import logging
import datetime
import threading

from agent import utils



class Database(object):
    """Represents a simple database"""
    def __init__(self, dm_filename, db_filename):
        """Initialize the DB from a file"""
        self._db_filename = db_filename
        self._file_write_lock = threading.Lock()
        self._new_inst_num_lock = threading.Lock()
        self._start_time = time.time()
        self._supported_insert_path_list = [
            "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic."
        ]
        self._supported_delete_path_list = [
            "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}."
        ]

        logger = logging.getLogger(self.__class__.__name__)
        logger.debug("Initializing the Database...")

        # Retrieve the Implemented Data Model
        with open(dm_filename, "r") as dm_in_json:
            try:
                self._dm = json.load(dm_in_json)
            except ValueError as parse_err:
                self._dm = {}
                logger.error("Implemented Data Model is NOT properly formatted JSON: %s", parse_err)

        # Retrieve the Persisted Database
        with open(db_filename, "r") as db_in_json:
            try:
                self._db = json.load(db_in_json)
            except ValueError as parse_err:
                self._db = {}
                logger.error("Persisted Database is NOT properly formatted JSON: %s", parse_err)


    def get(self, path):
        """Retrieve the value of the incoming path, or throw a NoSuchPathError"""
        if path in self._db:
            if self._db[path] == "__UPTIME__":
                return int(time.time() - self._start_time)
            elif self._db[path] == "__IPADDR__":
                return utils.IPAddr.get_ip_addr()
            elif self._db[path] == "__CURR_TIME__":
                time_zone = self._db["Device.Time.LocalTimeZone"]
                tz_part = time_zone.split(",")[0]
                now = datetime.datetime.now()
                now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
                if tz_part == "CST6CDT":
                    now_str += "-06:00"
                else:
                    now_str += "Z"
                return now_str
            elif self._db[path] == "__NUM_ENTRIES__":
                inst_path = re.sub(r'NumberOfEntries', '.', path)
                found_instances = self.find_instances(inst_path)
                return len(found_instances)
            else:
                return self._db[path]
        else:
            raise NoSuchPathError(path)

    def update(self, path, value):
        """Change the value of the incoming path, or throw a NoSuchPathError"""
        if path in self._db:
            self._db[path] = value
            self._save()
        else:
            raise NoSuchPathError(path)


    def find_params(self, path):
        """Retrieve a set of parameter paths that match the incoming path"""
        found_keys = []
        is_implemented_path = False
        logger = logging.getLogger(self.__class__.__name__)

        # Turn the incoming path into a regex to validate it is in the implemented data model
        dm_regex_str = self._dm_regex(path, path.endswith("."))
        logger.debug("find_params: Using regex \"%s\" to validate Path [%s] is in the Implemented Data Model",
                     dm_regex_str, path)

        # Turn the incoming path into a regex to get the matching paths
        db_regex_str = self._db_regex(path, path.endswith("."))
        logger.debug("find_params: Using regex \"%s\" to retrieve values from the Database for Path [%s]",
                     db_regex_str, path)

        # Validate that path is in the Implemented Data Model
        dm_keys = self._dm.keys()
        for dm_key in dm_keys:
            if re.fullmatch(dm_regex_str, dm_key) is not None:
                is_implemented_path = True
                break

        # If the path is Valid then retrieve the matching paths
        if is_implemented_path:
            db_keys = self._db.keys()
            for key in db_keys:
                if re.fullmatch(db_regex_str, key) is not None:
                    found_keys.append(key)
        else:
            raise NoSuchPathError(path)

        return found_keys

    def find_instances(self, partial_path):
        """Retrieve a set of object instance paths that match the incoming path"""
        found_keys = []
        is_implemented_path = False
        logger = logging.getLogger(self.__class__.__name__)

        if partial_path.endswith("."):
            # Turn the incoming path into a regex to validate it is in the implemented data model
            dm_regex_str = self._dm_regex(partial_path, True)
            logger.debug("find_instances: Using regex \"%s\" to validate Path [%s] is in the Implemented Data Model",
                         dm_regex_str, partial_path)

            # Turn the incoming path into a regex to get the matching paths
            db_regex_str = self._db_regex(partial_path, True)
            logger.debug("find_instances: Using regex \"%s\" to retrieve values from the Database for Path [%s]",
                         db_regex_str, partial_path)
        else:
            raise NoSuchPathError(partial_path)

        # length minus 1 due to the ending "." causing 1 more split
        partial_path_part_len = len(partial_path.split(".")) - 1

        # Validate that path is in the Implemented Data Model
        for dm_key in self._dm:
            if re.fullmatch(dm_regex_str, dm_key) is not None:
                # Validate that the partial_path is a multi-instance object
                dm_key_parts = dm_key.split(".")
                if dm_key_parts[partial_path_part_len] == "{i}":
                    is_implemented_path = True
                    break

        # If the path is Valid then retrieve the matching paths
        if is_implemented_path:
            for path in self._db:
                if re.fullmatch(db_regex_str, path) is not None:
                    # We only want the path to the next level (instance identifiers)
                    path_parts = path.split(".")
                    built_path = self._build_path_from_parts(path_parts, partial_path_part_len)
                    found_key = built_path + path_parts[partial_path_part_len] + "."

                    if not self._is_meta_parameter(path_parts, partial_path_part_len):
                        # Only add it to found_keys if we haven't do so already
                        if found_key not in found_keys:
                            found_keys.append(found_key)
        else:
            raise NoSuchPathError(partial_path)

        return found_keys


    def find_impl_objects(self, partial_path, next_level):
        """Retrieve a set of implemented object paths that match the incoming path"""
        found_keys = []
        is_implemented_path = False
        logger = logging.getLogger(self.__class__.__name__)
        generic_partial_path = self._generic_dm_path(partial_path)

        if partial_path.endswith("."):
            # Turn the incoming path into a regex to validate it is in the implemented data model
            dm_regex_str = self._dm_regex(partial_path, True)
            logger.debug(
                "find_impl_objects: Using regex \"%s\" to validate Path [%s] is in the Implemented Data Model",
                dm_regex_str, partial_path)
        else:
            raise NoSuchPathError(partial_path)

        # length minus 1 due to the ending "." causing 1 more split
        partial_path_part_len = len(partial_path.split(".")) - 1

        # Validate that path is in the Implemented Data Model
        for dm_key in self._dm:
            if re.fullmatch(dm_regex_str, dm_key) is not None:
                found_key = None
                key_parts = dm_key.split(".")
                key_parts_len = len(key_parts)
                is_implemented_path = True

                if next_level:
                    if key_parts_len > partial_path_part_len + 1:
                        built_path = self._build_path_from_parts(key_parts, partial_path_part_len)
                        found_key = built_path + key_parts[partial_path_part_len] + "."
                else:
                    inx = 0
                    found_key = ""
                    while inx < (key_parts_len - 1):
                        found_key += key_parts[inx]
                        found_key += "."
                        inx += 1

                # Only add it to found_keys if we haven't done so already
                if found_key is not None:
                    if found_key not in found_keys:
                        # Don't add the incoming partial_path
                        if not found_key == generic_partial_path:
                            found_keys.append(found_key)

        # If the path is Valid then retrieve the matching paths
        if not is_implemented_path:
            raise NoSuchPathError(partial_path)

        return found_keys

    def insert(self, partial_path):
        """Insert a new record in the table"""
        logger = logging.getLogger(self.__class__.__name__)

        if len(self.find_impl_objects(partial_path, True)) > 0:
            dm_regex_str = partial_path
            dm_regex_str = re.sub(r'\{(.+?)\}', '{i}', dm_regex_str)
            dm_regex_str = re.sub(r'\.\d\.', '.{i}.', dm_regex_str)
            logger.debug("insert: Using regex \"%s\" to validate Path [%s] is in the Supported Insert Path List",
                         dm_regex_str, partial_path)

            if dm_regex_str in self._supported_insert_path_list:
                next_inst_num_path = partial_path + "__NextInstNum__"
                with self._new_inst_num_lock:
                    next_inst_num = self.get(next_inst_num_path)
                    self.update(next_inst_num_path, next_inst_num + 1)

                if dm_regex_str == "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.":
                    self._db[partial_path + str(next_inst_num) + ".URL"] = ""
                    self._save()
                else:
                    raise NotImplementedError()
            else:
                raise NoSuchPathError(partial_path)
        else:
            raise NoSuchPathError(partial_path)

        return next_inst_num

    def delete(self, partial_path):
        """Remove an existing record from the table"""
        logger = logging.getLogger(self.__class__.__name__)

        if len(self.find_impl_objects(partial_path, True)) > 0:
            dm_regex_str = partial_path
            dm_regex_str = re.sub(r'\{(.+?)\}', '{i}', dm_regex_str)
            dm_regex_str = re.sub(r'\.\d\.', '.{i}.', dm_regex_str)
            logger.debug("delete: Using regex \"%s\" to validate Path [%s] is in the Supported Insert Path List",
                         dm_regex_str, partial_path)

            if dm_regex_str in self._supported_delete_path_list:
                if dm_regex_str == "Device.Services.HomeAutomation.{i}.Camera.{i}.Pic.{i}.":
                    del self._db[partial_path + "URL"]
                    self._save()
                else:
                    raise NotImplementedError()
            else:
                raise NoSuchPathError(partial_path)
        else:
            raise NoSuchPathError(partial_path)


    def _db_regex(self, path, partial_path):
        """Generate a regex for determining whether or note a path is in the DB"""
        db_regex_str = "^" + path
        # Assuming that the internal storage is instance number based
        db_regex_str = re.sub(r'\.\*\.', r'.[0-9]+.', db_regex_str)
        db_regex_str = re.sub(r'\.', r'\.', db_regex_str)

        if partial_path:
            db_regex_str = db_regex_str + ".*"

        return db_regex_str

    def _dm_regex(self, path, partial_path):
        """Generate a regex for determining whether or not a path is in the DM"""
        dm_regex_str = "^" + path  # Starts with
        dm_regex_str = re.sub(r'\.[0-9]+\.', r'.{i}.', dm_regex_str)  # Instance Number Addressing
        dm_regex_str = re.sub(r'\.\*\.', r'.{i}.', dm_regex_str)  # Wild-card Searching
        dm_regex_str = re.sub(r'\.', r'\.', dm_regex_str)  # Replace '.' with explicit '.' search

        if partial_path:
            dm_regex_str = dm_regex_str + ".*"

        return dm_regex_str

    def _generic_dm_path(self, path):
        """Turn a DM Path into a Generic one by replacing instance numbers and wildcards"""
        generic_path = re.sub(r'\.[0-9]+\.', r'.{i}.', path)  # Instance Number Addressing
        generic_path = re.sub(r'\.\*\.', r'.{i}.', generic_path)  # Wild-card Searching

        return generic_path

    def _build_path_from_parts(self, path_parts, partial_path_part_len):
        """Build a search path from the tokenized path (path parts)"""
        built_path = ""
        built_path_part_count = 0

        # We only want the path to the next level (instance identifiers)
        for part in path_parts:
            built_path_part_count += 1
            built_path = built_path + part + "."
            if built_path_part_count == partial_path_part_len:
                break

        return built_path

    def _is_meta_parameter(self, path_parts, partial_path_part_len):
        """Determine if the parameter is a meta parameter"""
        return path_parts[partial_path_part_len].startswith("__") and \
               path_parts[partial_path_part_len].endswith("__")

    def _save(self):
        """Save the contents of the DB back into the File"""
        with self._file_write_lock:
            with open(self._db_filename, "w") as db_file:
                json.dump(self._db, db_file)



class NoSuchPathError(Exception):
    """A Database NoSuchPath Error"""
    def __init__(self, value):
        """Initialize the Exception"""
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        """Return the String value of the Exception"""
        return repr(self.value)
