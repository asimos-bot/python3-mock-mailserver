#!/usr/bin/env python3
import unittest
import os

from pathlib import Path

from database import Database
from database import EmailDoesNotExist

class DatabaseTests(unittest.TestCase):

    def test_email_check(self):

        # bad addresses
        for email in [
                # size min
                "",
                "@gmail.com",
                "dafasd@.com",
                "asdfasdf@asdfasd.c"
                # size max
                "12345678901234567890123456789012345678901@gmail.com",
                "123456@12345678901.com",
                "email@gmail.coma",
                # ignore separators
                "hello.howareyou.com",
                "gadg@dafadfdafdfa",
                # invalid characters at prefix
                "~asdf@gmail.com",
                "aadsf^@gmail.com",
                "&asdfad@gmail.com",
                "'asdf@gmail.com",
                "éasdfa@gmail.com",
                "ṕasdf@gmail.com",
                "çsadfsd@gmail.com",
                # invalid characters at middle
                "example@éadfa.com",
                "example@ãdfa",
                # invalid characters at the end
                "asdfas@gadfa.122,"
                "@adf.coç",
                # whitespace
                " asdf@asdf.com",
                "carroda@ gmail.com",
                "aacento@gmail .com",
                "masaqui@psde. com",
                "eacentoaqui@pode.cpm "]:
            self.assertFalse( Database.check_email(email) )

        # good addresses
        for email in [
                "asimos@gmail.com",
                "good4u@a.com",
                "a@a.uk",
                "23423@32432.com",
                "1234567890123456789012345678901234567890@1234567890.com"]:
            self.assertTrue( Database.check_email(email) )

    def test_add_to_mailbox(self):

        emails = ["a@a.uk", "asimos@gmail.com"]
        directory = Path("test_database")
        email_path = Path(directory, emails[0])

        if( email_path.exists() ): os.remove(email_path)
        if( directory.exists() ): os.rmdir(directory)

        database = Database(directory, emails)
        self.assertTrue(database.emails == emails)

        self.assertRaises(
            EmailDoesNotExist,
            database.add_to_mailbox,
            "a@a.ua",
            "To: a@a.ua\nFrom: anonymous\nLet's play untrusted")

        database.add_to_mailbox(emails[0], "test123")
        with open(email_path) as f:
            self.assertTrue( f.read() == "test123" )

if __name__ == '__main__':
    unittest.main()
