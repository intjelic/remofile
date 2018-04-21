# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, April 2018

#import os
#import threading
#from tempfile import mkstemp
#from tempfile import TemporaryDirectory
#import unittest
#from remofile.server import Server
#from remofile.client import Client
#from remofile.token import generate_token
#from remofile.protocol import *

#HOSTNAME = '127.0.0.1'
#PORT     = 6768
#TOKEN    = generate_token()

#class TestClient(unittest.TestCase):
    #""" Test the client class.

    #To be written.
    #"""

    #def setUp(self):
        ## create a temporary served directory
        #self.served_directory = TemporaryDirectory()

        ## start the server in an external thread
        #self.server = Server(self.served_directory.name, TOKEN)

        #def server_loop(server):
            #server.run(HOSTNAME, PORT)

        #self.server_thread = threading.Thread(target=server_loop, args=(self.server,))
        #self.server_thread.start()

    #def tearDown(self):
        ## terminate the server and wait until it terminates
        #self.server.terminate()
        #self.server_thread.join()

        ## delete all testing contents in served directory
        #self.served_directory.cleanup()

    #def test_upload_files(self):
        #""" Test foobar.

        #To be written.
        #"""

        # to be implemented
        # test 3 options to alter log behavior
        # test 2 options to ignore file exceeding a given size

        #pass

    #def test_download_files(self):
        #""" Test foobar.

        #To be written.
        #"""

        #pass

    #def test_synchronize_upload(self):
        #""" Test foobar.

        #To be written.
        #"""

        #pass

    #def test_synchronize_download(self):
        #""" Test foobar.

        #To be written.
        #"""

        #pass
