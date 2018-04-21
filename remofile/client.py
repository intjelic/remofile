# Remofile - Embeddable alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
from pathlib import PosixPath
import zmq
from remofile.protocol import *

# TimeoutError

# FileExistsError
# FileNotFoundError
# InterruptedError
# IsADirectoryError
# NotADirectoryError
# PermissionError


class InvalidFileName(Exception):
    pass

class BadRequestError(Exception):
    pass

class UnknownError(Exception):
    pass

CHUNK_SIZE = 4096

class FileClient:
    """ Remofile client.

    This class implements a synchronous client to a Remofile directory;
    in other words all file operations are blocking. It doens't maintain
    an active connection with the server, instead you use a timeout
    value.

    The basic file operations are.

        - listing files in the remote directory
        - making directories in the remote directory
        - uploading a file to the remote directory
        - downloading a file from the remote directory
        - deleting a file in the remote directory
        - deleting a folder in the remote directory

    Exceptions are raised whenever a file operation couldn't be
    completed or if an unexpected error occured.
    """

    def __init__(self, hostname, port, token):
        """ Initialize the client.

        It initializes the client with the hostname, port and the
        token.
        """

        self.token = bytes(token, 'utf-8')

        context = zmq.Context.instance()

        self.socket_address = 'tcp://{0}:{1}'.format(hostname, str(port))

        self.socket = context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.IDENTITY, self.token)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.socket_address)

    def __del__(self):
        self.socket.disconnect(self.socket_address)

    def list_files(self, directory, timeout=None):
        """ List files of a given directory in the remote directory.

        - directory accept any PathLike

        - should be a absolute path, if not this is relative to the root directory

        May raise
        """

        # get a string representation of the directory
        directory = os.fspath(directory)

        # send list files request and wait for answer according to the
        # timeout value
        request = make_list_files_request(directory)
        self.socket.send_pyobj(request)

        if self.socket.poll(timeout) & zmq.POLLIN:
            response = self.socket.recv_pyobj()
        else:
            raise TimeoutError

        # handle response
        response_type = response[0]

        if response_type == Response.ACCEPTED:
            assert response[1] == Reason.FILES_LISTED
            files_list = response[2]
            return files_list
        elif response_type == Response.REFUSED:
            if response[1] == Reason.NOT_A_DIRECTORY:
                raise NotADirectoryError
            else:
                raise NotImplementedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

        raise NotImplementedError

    def create_file(self, name, directory, timeout=None):
        """ Create a file in the remote directory.

        Long description here.
        """

        # send create file request and wait for answer according to the
        # timeout value
        request = make_create_file_request(name, directory)
        self.socket.send_pyobj(request)

        if self.socket.poll(timeout) & zmq.POLLIN:
            response = self.socket.recv_pyobj()
        else:
            raise TimeoutError

        # handle response
        response_type = response[0]

        if response_type == Response.ACCEPTED:
            reason_type = response[1]
            assert reason_type == Reason.FILE_CREATED
        elif response_type == Response.REFUSED:
            reason_type = response[1]
            if reason_type == Reason.INVALID_FILE_NAME:
                raise InvalidFileName
            elif reason_type == Reason.NOT_A_DIRECTORY:
                raise NotADirectoryError
            elif reason_type == Reason.FILE_ALREADY_EXISTS:
                raise FileExistsError
            else:
                raise NotImplementedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

    def make_directory(self, name, directory, timeout):
        """ Create a directory in the remote directory.

        It creates an empty directory with a given name in a given
        directory located in the remote directory.

        May raise NotADirectoryError exception if the destination
        directory doesn't exist or FileExistsError if a directory (or a
        file) with that name already exists.

        If the operation takes longer than the given timeout, a
        TimeoutError exception is raised.
        """

        # send make directory request and wait for answer according to
        # the timeout value
        request = make_make_directory_request(name, directory)
        self.socket.send_pyobj(request)

        response = self.socket.recv_pyobj()

        # process response and raise exceptions if file operation
        # couldn't completed for some reasons
        response_type = response[0]

        if response_type == Response.ACCEPTED:
            reason_type = response[1]
            assert reason_type == Reason.DIRECTORY_CREATED
        elif response_type == Response.REFUSED:
            reason_type = response[1]
            if reason_type == Reason.NOT_A_DIRECTORY:
                raise NotADirectoryError
            elif reason_type == Reason.FILE_ALREADY_EXISTS:
                raise FileExistsError
            else:
                raise NotImplementedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

    def upload_file(self, source, destination, chunk_size=CHUNK_SIZE, process_chunk=None, timeout=None):
        """ Upload a file to the remote directory.

        - source must be a valid file, readable
        ## how about regex ?
        ## source must be a file, or a directory, relative to getcwd()
        ## destination must be a directory, relative to build directory
        ## exlude files, a list of files, relative to source

        Examples:

            foobar

        Long description.
        """

        # compute destination directory and file name from source
        source = PosixPath(source)

        name      = source.name
        directory = source.parent
        assert name != ''

        # open source file and read its size
        source_file = source.open('rb')
        source_file.seek(0, os.SEEK_END)
        file_size = source_file.tell()
        source_file.seek(0, os.SEEK_SET)

        # make sure chunk size is valid
        assert chunk_size > 0

        # initiate upload file process
        request = make_upload_file_request(name, destination, file_size, chunk_size)
        self.socket.send_pyobj(request)
        response = self.socket.recv_pyobj()

        if response[0] != Response.ACCEPTED:
            print(response)
            raise NotImplementedError

        assert response[1] == Reason.TRANSFER_ACCEPTED

        # send data chunks until the upload is completed
        transfer_completed = False
        last_chunk = False

        while not transfer_completed:

            # compute remaining bytes left to read
            remaining_bytes = file_size - source_file.tell()

            if remaining_bytes <= chunk_size:
                last_chunk = True

            # read next data chunk from the file
            chunk_data = source_file.read(chunk_size)

            # send data chunk and wait for response
            request = make_send_chunk_request(chunk_data)
            self.socket.send_pyobj(request)
            response = self.socket.recv_pyobj()

            # error response aren't handled yet
            response_type = response[0]

            if response_type != Response.ACCEPTED:
                raise NotImplementedError

            # foobar
            reason_type = response[1]

            if last_chunk:
                assert reason_type == Reason.TRANSFER_COMPLETED
                transfer_completed = True
            else:
                assert reason_type == Reason.CHUNK_RECEIVED

            if not last_chunk:
                if process_chunk:
                    should_continue = process_chunk(chunk_data, remaining_bytes, file_size)

                    if not should_continue:
                        request = make_cancel_transfer_request()
                        self.socket.send_pyobj(request)

                        response = self.socket.recv_pyobj()

                        print(response)
                        if response[0] == Response.ACCEPTED:
                            raise NotImplementedError

                        assert response[1] == Reason.TRANSFER_CANCELLED

                        transfer_completed = True

    def download_file(self, source, destination, chunk_size=CHUNK_SIZE, process_chunk=None, timeout=None):

        # compute destination directory and file name from source
        directory = os.path.dirname(source)
        name      = os.path.basename(source)
        assert name != ''

        # adjust destination path to be an absolute path
        if not os.path.isabs(destination):
            destination = os.path.join(os.getcwd(), destination)

        # todo: check if path actually exist

        print(directory)
        print(name)
        print(destination)

        request = make_download_file_request(name, directory, chunk_size)
        self.socket.send_pyobj(request)

        response = self.socket.recv_pyobj()
        print(response)

        #assert response[0] == Response.ACCEPTED
        #response_type, reason_type, file_size = response

        #destination_file = open(destination, 'wb')

        #transfer_completed = False

        #while not transfer_completed:

            #request = make_receive_chunk_request()
            #self.socket.send_pyobj(request)

            #response = self.socket.recv_pyobj()

            #assert response[0] == Response.ACCEPTED

            #_, reason_type, chunk_data = response

            #if reason == Reason.TRANSFER_COMPLETED:
                #transfer_completed = True
                #return

            #assert reason_type == Reason.CHUNK_SENT

            #self.file.write(chunk_data)


        #raise NotImplementedError

    def delete_file(self):
        raise NotImplementedError

    def _process_error_response(self, response):
        reason_type = response[1]

        if reason_type == Reason.BAD_REQUEST:
            raise BadRequestError
        elif reason_type == Reason.UNKNOWN_ERROR:
            error_message = response[2]
            raise UnknownError(error_message)
        else:
            raise NotImplementedError
