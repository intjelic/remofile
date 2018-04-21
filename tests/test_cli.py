# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import unittest

class TestCLI(unittest.TestCase):
    """ Test the command-line interface.

    To be written.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_upload_command(self):
        """ Test the upload command.

        Long description.
        """

        # create remote working directory tree
        # /foo/
        #      bar/   -> existing directory
        #      qaz    -> existing file
        #
        # test uploading directory with no recursive flag enabled
        #  - bar
        #  - foo
        #
        # test uploading to incorrect destination directory
        #  - root directory (/)
        #  - directory whose parent is an unexsiting directory (/foo/qaz/bar)
        #  - directory whose parent is an existing directory but is an unexisting directory (/foo/qaz)
        #  - directory whose parent is an existing directory but is a existing file (/foo/qaz)
        #
        # test uploading a file that conflict with existing file (or
        # directory)
        #  - foo
        #  - bar
        #

    def test_bar(self):
        pass
