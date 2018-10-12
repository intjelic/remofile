# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
from multiprocessing import Process
from pathlib import PosixPath
from tempfile import TemporaryDirectory
import unittest
import zmq
from remofile.server import Server
from remofile.token import generate_token
from remofile.protocol import *

HOSTNAME = '127.0.0.1'
PORT     = 6768
TOKEN    = generate_token()

def make_bad_request(request_type):
    return (request_type, 'this', 'is', 'a', 'bad', 'request')

class TestProtocol(unittest.TestCase):
    """ Test the transfer file protocol.

    It consists of testing all request methods and their possible
    responses.
    """

    def setUp(self):
        # create remote working directory
        self.remote_directory = TemporaryDirectory()
        self.remote_directory_path = PosixPath(self.remote_directory.name)

        # start the server in a child process
        def server_target(root_directory):
            server = Server(root_directory, TOKEN)

            import signal

            def handle_sigterm(signum, frame):
                handle_sigterm.server.terminate()

            handle_sigterm.server = server

            signal.signal(signal.SIGTERM, handle_sigterm)

            server.run(HOSTNAME, PORT)

        self.server_process = Process(target=server_target, args=(self.remote_directory_path,))
        self.server_process.start()

    def tearDown(self):
        # terminate the server (send SIGTERM) and wait until child process
        # terminates
        self.server_process.terminate()
        self.server_process.join()

        # delete all testing contents in served directory
        self.remote_directory.cleanup()

    def create_temporary_file(self, directory, name, size):
        """ Create a temporary file in the 'remote' directory.

        This function creates a temporary file with a given name in a
        given directory located in the temporary workinng 'remote'
        directory. It's filled with a given amount of random data.

        It returns a posix path of the created file and the generated
        data.
        """

        assert os.path.isabs(directory) == True
        directory = directory[1:]

        file_data = os.urandom(size)

        temporary_file_path = self.remote_directory_path / directory / name
        temporary_file = temporary_file_path.open('wb')
        temporary_file.write(file_data)
        temporary_file.close()

        return temporary_file_path, file_data

    def create_temporary_directory(self, directory, name):
        """ Create a temporary directory in the 'remote' directory.

        This function creates a temporary directory with a given name
        in a given directory located in the temporary workinng 'remote'
        directory.

        It returns a posix path of the created directory.
        """

        assert os.path.isabs(directory) == True
        directory = directory[1:]

        temporary_directory_path = self.remote_directory_path / directory / name
        temporary_directory_path.mkdir(exist_ok=False)

        return temporary_directory_path

    def test_list_files_request(self):
        """ Test the LIST_FILE request.

        It starts with constructing the following working tree and
        subsequently tests during the creation if listing files of
        these two folders return the correct list of files.

            /foo.bin
             bar/qaz.txt

        It ends with testing listing files of a non-existing directory.
        """

        # create socket and connect to the server
        context = zmq.Context.instance()

        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, bytes(TOKEN, 'utf-8'))
        socket.connect('tcp://{0}:{1}'.format(HOSTNAME, str(PORT)))

        # test listing files of (empty) root directory
        expected_response = (Response.ACCEPTED, Reason.FILES_LISTED, {})

        for list_directory in ('/', ''):
            request = make_list_files_request(list_directory)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_response)

        # test listing files of root directory  after creating 'foo.bin'
        # and 'bar/' in it
        file_path, _ = self.create_temporary_file('/', 'foo.bin', 1052)
        directory_path = self.create_temporary_directory('/', 'bar')

        expected_files_list= {
            'foo.bin' : (False, 1052, file_path.stat().st_atime),
            'bar'     : (True,     0, directory_path.stat().st_atime)
        }

        for list_directory in ('/', ''):
            request = make_list_files_request(list_directory)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()

            response_type, reason_type, files_list = response

            self.assertEqual(response_type, Response.ACCEPTED)
            self.assertEqual(reason_type, Reason.FILES_LISTED)
            self.assertDictEqual(files_list, expected_files_list)

        # test listing files of (empty) bar/ directory
        expected_response = (Response.ACCEPTED, Reason.FILES_LISTED, {})

        for list_directory in ('/bar', 'bar'):
            request = make_list_files_request(list_directory)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_response)

        # test listing files of bar/ directory after creating qaz.txt in
        # it
        file_path, _ = self.create_temporary_file('/bar', 'qaz.txt', 1024)

        expected_files_list= {
            'qaz.txt' : (False, 1024, file_path.stat().st_atime),
        }

        for list_directory in ('/bar', 'bar'):
            request = make_list_files_request(list_directory)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()

            response_type, reason_type, files_list = response
            self.assertEqual(response_type, Response.ACCEPTED)
            self.assertEqual(reason_type, Reason.FILES_LISTED)
            self.assertDictEqual(files_list, expected_files_list)

        # test listing files of a directory that doesn't exist
        expected_response = (Response.REFUSED, Reason.FILE_NOT_FOUND)

        request = make_list_files_request('/foo')
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test listing files of a directory that actually is a file
        expected_response = (Response.REFUSED, Reason.NOT_A_DIRECTORY)

        request = make_list_files_request('/foo.bin')
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

    def test_create_file_request(self):
        """ Test the CREATE_FILE request.

        It starts with creating a temporary working tree of files.

          foo/
            bar.bin

        Then, it attemps to create a file 'qaz.bin' in 'foo/' directory.

        But before, it tests the create file  request by sending several
        invalid requests.

          * Send a bad request
          * Send the four invalid requests expecting the three variant of refused responses

        The last step is sending a valid request and check if the file
        has effectively been created at the right location.
        """

        # create socket and connect to the server
        context = zmq.Context.instance()

        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, bytes(TOKEN, 'utf-8'))
        socket.connect('tcp://{0}:{1}'.format(HOSTNAME, str(PORT)))

        # create temporary working tree of files
        self.create_temporary_directory('/', 'foo')
        self.create_temporary_file('/foo', 'bar.bin', 1024)

        # prepare common variables
        name       = 'qaz.bin'
        directory  = '/foo'

        # test sending invalid create file request because it's badly
        # formatted
        expected_response = (Response.ERROR, Reason.BAD_REQUEST)

        request = make_bad_request(Request.CREATE_FILE)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid create file request because the file name
        # is invalid
        invalid_names = ['*baz', 'b"az', 'baz|']
        expected_response = (Response.REFUSED, Reason.INVALID_FILE_NAME)

        for invalid_name in invalid_names:
            request = make_create_file_request(invalid_name, directory)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_response)

        # test sending invalid create file request because it has a
        # non-existing directory
        incorrect_directory = '/bar'
        expected_response = (Response.REFUSED, Reason.FILE_NOT_FOUND)

        request = make_create_file_request(name, incorrect_directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid create file request because it has a
        # the directory refers to a file
        incorrect_directory = '/foo/bar.bin'
        expected_response = (Response.REFUSED, Reason.NOT_A_DIRECTORY)

        request = make_create_file_request(name, incorrect_directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid create file request because it the file
        # name conflicts with an existing file (or directory)
        incorrect_name = 'bar.bin'
        expected_response = (Response.REFUSED, Reason.FILE_ALREADY_EXISTS)

        request = make_create_file_request(incorrect_name, directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending valid create file request and test if the file
        # has effectively been created before and after the request
        expected_response = (Response.ACCEPTED, Reason.FILE_CREATED)

        created_file_path = self.remote_directory_path / directory[1:] / name
        self.assertFalse(created_file_path.exists())

        request = make_create_file_request(name, directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        self.assertTrue(created_file_path.is_file())

    def test_make_directory_request(self):
        """ Test the MAKE_DIRECTORY request.

        It starts with creating a temporary working tree of files.

          foo/
            bar/
          foo.bin

        Then, it attemps to create a directory 'qaz/' in 'foo/'
        directory.

        But before, it tests the create directory request by sending
        several invalid requests.

          - Send a bad request
          - Send the four invalid requests expecting the three variant of refused responses

        The last step is sending a valid request and check if the
        directory has effectively been created at the right location.
        """

        # create socket and connect to the server
        context = zmq.Context.instance()

        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, bytes(TOKEN, 'utf-8'))
        socket.connect('tcp://{0}:{1}'.format(HOSTNAME, str(PORT)))

        # create temporary working tree of files
        self.create_temporary_directory('/', 'foo')
        self.create_temporary_directory('/foo', 'bar')
        self.create_temporary_file('/', 'foo.bin', 1024)

        # prepare common variables
        name      = 'qaz'
        directory = '/foo'

        # test sending invalid make directory request because it's badly
        # formatted
        expected_response = (Response.ERROR, Reason.BAD_REQUEST)

        request = make_bad_request(Request.MAKE_DIRECTORY)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid make directory request because the
        # directory name is incorrect
        invalid_names = ['*baz', 'b"az', 'baz|']
        expected_response = (Response.REFUSED, Reason.INVALID_FILE_NAME)

        for invalid_name in invalid_names:
            request = make_make_directory_request(invalid_name, directory)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_response)

        # test sending invalid make directory request because it has a
        # non-existing directory
        incorrect_directory = '/bar'
        expected_response = (Response.REFUSED, Reason.FILE_NOT_FOUND)

        request = make_make_directory_request(name, incorrect_directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid make directory request because the
        # directory refers to a file
        incorrect_directory = '/foo.bin'
        expected_response = (Response.REFUSED, Reason.NOT_A_DIRECTORY)

        request = make_make_directory_request(name, incorrect_directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid make directory request because the
        # directory name conflicts with an existing directory (or file)
        incorrect_name = 'bar'
        expected_response = (Response.REFUSED, Reason.FILE_ALREADY_EXISTS)

        request = make_make_directory_request(incorrect_name, directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending valid make directory request and check if the
        # directory has effectively been created at the right location
        expected_response = (Response.ACCEPTED, Reason.DIRECTORY_CREATED)

        created_directory_path = self.remote_directory_path / directory[1:] / name
        self.assertFalse(created_directory_path.exists())

        request = make_make_directory_request(name, directory)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        self.assertTrue(created_directory_path.is_dir())

    def test_upload_file_request(self):
        """ Test the upload request-response cycle.

        It starts with creating a temporary working tree of files.

          foo/
            bar.bin

        Then, it attempts to upload a file 'qaz.bin' to the 'foo/'
        directory.

        But before, it tests the upload request by sending several
        invalid requests.

          - Send a bad request
          - Send the four invalid requests expecting the four variant of refused responses
          - Send a valid request, but send invalid chunks later
          - Send a valid request, but cancel transfer later

        The last step is sending a valid request and sending sent chunk
        requests until completion of the upload.

        It finishes with testing if the uploaded file has effectively
        been created at the right location and has the correct binary
        content.
        """

        # create socket and connect to the server
        context = zmq.Context.instance()

        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, bytes(TOKEN, 'utf-8'))
        socket.connect('tcp://{0}:{1}'.format(HOSTNAME, str(PORT)))

        # create temporary working tree of files
        self.create_temporary_directory('/', 'foo')
        self.create_temporary_file('/foo', 'bar.bin', 1024)

        # prepare common variables
        name       = 'qaz.bin'
        directory  = '/foo'
        file_size  = 1052
        chunk_size = 512

        # test sending invalid upload file request because it's badly
        # formatted
        expected_response = (Response.ERROR, Reason.BAD_REQUEST)

        request = make_bad_request(Request.UPLOAD_FILE)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid upload file request because it's has a
        # non-existing directory
        incorrect_directory = '/bar'
        expected_response = (Response.REFUSED, Reason.NOT_A_DIRECTORY)

        request = make_upload_file_request(name, incorrect_directory, file_size, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()

        self.assertTupleEqual(response, expected_response)

        # test sending invalid upload file request because a file with
        # that name already exists
        incorrect_name = 'bar.bin'
        expected_response = (Response.REFUSED, Reason.FILE_ALREADY_EXISTS)

        request = make_upload_file_request(incorrect_name, directory, file_size, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid upload file request because the file size
        # is incorrect
        incorrect_file_sisze = 0
        expected_response = (Response.REFUSED, Reason.INCORRECT_FILE_SIZE)

        request = make_upload_file_request(name, directory, incorrect_file_sisze, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid upload file request because it has an
        # incorrect chunk size
        incorrect_chunk_size = 0
        expected_response = (Response.REFUSED, Reason.INCORRECT_CHUNK_SIZE)

        request = make_upload_file_request(name, directory, file_size, incorrect_chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending valid upload file request, then send one valid
        # chunk followed by one invalid chunk
        valid_chunk_data   = bytes(chunk_size)
        invalid_chunk_data = bytes(chunk_size - 1)

        expected_responses = (
            (Response.ACCEPTED, Reason.CHUNK_RECEIVED),
            (Response.ERROR, Reason.BAD_REQUEST)
        )

        request = make_upload_file_request(name, directory, file_size, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED))

        request = make_send_chunk_request(valid_chunk_data)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_responses[0])

        request = make_send_chunk_request(invalid_chunk_data)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()

        self.assertTupleEqual(response, expected_responses[1])

        # test sending valid upload file request, then send one valid
        # chunk followed by a cancel transfer request
        chunk_data = bytes(chunk_size)

        expected_responses = (
            (Response.ACCEPTED, Reason.CHUNK_RECEIVED),
            (Response.ACCEPTED, Reason.TRANSFER_CANCELLED)
        )

        request = make_upload_file_request(name, directory, file_size, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED))

        request = make_send_chunk_request(chunk_data)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_responses[0])

        request = make_cancel_transfer_request()
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_responses[1])

        # test sending valid upload file request, send valid chunks
        # until completion of upload
        file_data = os.urandom(file_size)
        chunks = (file_data[:512], file_data[512:1024], file_data[1024:])

        expected_responses = (
            (Response.ACCEPTED, Reason.CHUNK_RECEIVED),
            (Response.ACCEPTED, Reason.CHUNK_RECEIVED),
            (Response.ACCEPTED, Reason.TRANSFER_COMPLETED)
        )

        request = make_upload_file_request(name, directory, file_size, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED))

        for i in range(3):
            request = make_send_chunk_request(chunks[i])
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_responses[i])

        # verify if uploaded file is at the right location and has the
        # same binary data
        uploaded_file_path = self.remote_directory_path / directory[1:] / name
        self.assertTrue(uploaded_file_path.is_file())

        uploaded_file = uploaded_file_path.open('rb')
        self.assertEqual(file_data, uploaded_file.read())
        uploaded_file.close()

    def test_download_file_request(self):
        """ Test the download request-response cycle.

        It starts with creating a temporary working tree of files.

          foo/
            bar.bin
            qaz/

        Then, it attemps to download 'bar.bin' from 'foo/' directory.

        But before, it tests the download request by sending several
        invalid requests.

          - Send a bad request
          - Send the four invalid requests expecting the four variant of refused responses
          - Send a valid request, but send invalid chunks later
          - Send a valid request, but cancel transfer later

        The last step is sending a valid request and sending receive chunk
        requests until completion of the upload.
        """

        # create socket and connect to the server
        context = zmq.Context.instance()

        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, bytes(TOKEN, 'utf-8'))
        socket.connect('tcp://{0}:{1}'.format(HOSTNAME, str(PORT)))

        # create temporary working tree of files
        self.create_temporary_directory('/', 'foo')
        _, file_data = self.create_temporary_file('/foo', 'bar.bin', 1052)
        self.create_temporary_directory('/foo', 'qaz')

        # prepare common variables
        name       = 'bar.bin'
        directory  = '/foo'
        file_size  = 1052
        chunk_size = 512

        # test sending invalid download file request because it's badly
        # formatted
        expected_response = (Response.ERROR, Reason.BAD_REQUEST)

        request = make_bad_request(Request.DOWNLOAD_FILE)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid download file request because the chunk
        # size is incorrect
        incorrect_chunk_size = 0
        expected_response = (Response.REFUSED, Reason.INCORRECT_CHUNK_SIZE)

        request = make_download_file_request(name, directory, incorrect_chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid download file request because the file
        # name is incorrect
        invalid_names = ['*baz', 'b"az', 'baz|']
        expected_response = (Response.REFUSED, Reason.INVALID_FILE_NAME)

        for invalid_name in invalid_names:
            request = make_download_file_request(invalid_name, directory, chunk_size)
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_response)

        # test sending invalid download file request because it has
        # a non-existing directory
        incorrect_directory = '/qaz'
        expected_response = (Response.REFUSED, Reason.NOT_A_DIRECTORY)

        request = make_download_file_request(name, incorrect_directory, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid download file request because it has a
        # file that doesn't exist
        incorrect_name = 'qaz.bin'
        expected_response = (Response.REFUSED, Reason.FILE_NOT_FOUND)

        request = make_download_file_request(incorrect_name, directory, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending invalid download file request because it has a
        # name that refers to a directory instead of a file
        incorrect_name = 'qaz'
        expected_response = (Response.REFUSED, Reason.NOT_A_FILE)

        request = make_download_file_request(incorrect_name, directory, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_response)

        # test sending valid download file request, then send one valid
        # receive request followed by a cancel transfer request
        expected_responses = (
            (Response.ACCEPTED, Reason.CHUNK_SENT, file_data[:512]),
            (Response.ACCEPTED, Reason.TRANSFER_CANCELLED)
        )

        request = make_download_file_request(name, directory, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED, file_size))

        request = make_receive_chunk_request()
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_responses[0])

        request = make_cancel_transfer_request()
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, expected_responses[1])

        # test sending valid download file request, send receive chunks
        # requests until completion of download
        expected_responses = (
            (Response.ACCEPTED, Reason.CHUNK_SENT, file_data[:512]),
            (Response.ACCEPTED, Reason.CHUNK_SENT, file_data[512:1024]),
            (Response.ACCEPTED, Reason.TRANSFER_COMPLETED, file_data[1024:])
        )

        request = make_download_file_request(name, directory, chunk_size)
        socket.send_pyobj(request)

        response = socket.recv_pyobj()
        self.assertTupleEqual(response, (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED, file_size))

        for i in range(3):
            request = make_receive_chunk_request()
            socket.send_pyobj(request)

            response = socket.recv_pyobj()
            self.assertTupleEqual(response, expected_responses[i])

    def test_remove_file_request(self):
        """ Test the REMOVE_FILE request

        Long description.
        """

        pass
