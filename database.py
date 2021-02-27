#!/usr/bin/env python3
import os
import csv
import re

from pathlib import Path
from typing import List

class InvalidEmailAddressFormat(Exception):
    pass

class EmailDoesNotExist(Exception):
    pass

class Database:
    def __init__(self, directory: str, emails: List[str]):

        directory = Path(directory)

        self.check(directory, emails)

        self.directory = directory
        self.emails = emails

    def check(self, directory: Path, emails: List[str]):

        self.check_permissions(directory)
        for email in emails:
            if( not Database.check_email(email) ):
                raise InvalidEmailAddressFormat("Email " + email + " is invalid")

    def check_permissions(self, directory: Path):

        # create directory if it doesn't exist
        if( not directory.exists() ):
            os.mkdir(directory, 0o700)
        else:
            if( not directory.is_dir() ):
                raise NotADirectoryError(directory + " is not a directory")

            if( not ( os.access(directory, os.R_OK) and os.access(directory, os.W_OK) ) ):
                raise PermissionError("We can't read or write on directory " + directory)

    @classmethod
    def check_email(cls, email: str):
        return bool(re.search(r'^[a-z0-9.]{1,40}@[a-z0-9]{1,10}\.[a-z]{2,3}$', email))

    def does_email_exist(self, email: str):
        return email in self.emails

    def add_to_mailbox(self, email_address: str, data: str) -> bool:

        if( not self.does_email_exist(email_address) ):
            raise EmailDoesNotExist("Email " + email_address + " is not on our database")

        filepath = Path( self.directory, email_address )
        with open(filepath, "a") as f:
            f.write(data)
