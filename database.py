#!/usr/bin/env python3
import os
import csv
from pathlib import Path
import re

class AddressFileFormatError(Exception):
    pass

class Database:
    # All files must be inside the given directory, including the file
    # with the addresses
    # Second argument is optional, if it is not given, the list of
    # addresses will be search in "directory/index.txt"
    def __init__(self, directory, index):

        index = Path(directory, index) if directory not in index else Path(index)
        directory = Path(directory)

        self.check(directory, index)

        self.directory = directory
        self.index = index

    def check(self, directory, index):

        self.check_permissions(directory, True)
        self.check_permissions(index, False)
        self.check_index_format(index)

    def check_permissions(self, f, is_dir):

        if( not f.exists() ):
            raise FileNotFoundError()

        if( f.is_dir() != is_dir ):
            if( is_dir ):
                raise NotADirectoryError()
            else:
                raise IsADirectoryError()

        if( not ( os.access(f, os.R_OK) and os.access(f, os.W_OK) ) ):
            raise PermissionError()

    @classmethod
    def check_email(cls, email):
        return bool(re.search(r'^[a-z0-9.]{1,40}@[a-z0-9]{1,10}\.[a-z]{2,3}$', email))

    def check_index_format(self, index):

        with open('todo.txt') as f:
            try:
                reader = csv.DictReader(f)
                if(reader.fieldnames != ['address']):
                    raise AddressFileFormatError("Index file has the wrong format")
            except:
                raise AddressFileFormatError("Index file has the wrong format")

            # iterate over rows and check that every address is valid
            for row in reader:
                if( Database.check_email( row["address"] ) ):
                    raise InvalidAddressFormat("Found address in index file with invalid format: {}".format(row["address"]))
