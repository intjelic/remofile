# Remofile - Embeddable alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
import os.path
from pathlib import PosixPath
from enum import Enum
from tempfile import mkstemp
import shutil
import zmq
from remofile.protocol import *
from remofile.utils import is_file_name_valid

FILE_SIZE_LIMIT    = 4294967296
MINIMUM_CHUNK_SIZE = 512
MAXIMUM_CHUNK_SIZE = 8192

ServerState = Enum('ServerState', ['IDLE', 'UPLOAD', 'DOWNLOAD', 'DELETE'])

def normalize_directory(directory):
    """ Normalize a directory.

    Normalizing a directory consists of turning into a relative
    directory, even it initially was a relative directory.

        /foo/bar/qaz -> foo/bar/qaz
        foo/bar/qaz  -> foo/bar/qaz

    A normalized directory can be combined with the root directory.
    """

    return directory.relative_to(directory.root)

class FileServer:
    """ Remofile server.

    This class implements a Remofile server as specified by the
    protocol. It handles one client at a time.

        - start()/stop() to start threaded mode
        - run() to start no thread mode

    Raise NotADirectoryError if the root directory doesn't exist
    Raise ValueError if chunk size parametesr are incorrect (mini chunk
    size must be greather than 0 and maxi chunk size must be greater or
    equal to mini chunk size).
    Raise ValueError if file size limit is incorrect
    """

    def __init__(self,
        root_directory,
        token,
        file_size_limit = FILE_SIZE_LIMIT,
        min_chunk_size  = MINIMUM_CHUNK_SIZE,
        max_chunk_size  = MAXIMUM_CHUNK_SIZE
        ):

        self.root_directory = PosixPath(os.getcwd(), root_directory)

        if not self.root_directory.exists() or self.root_directory.is_file():
            raise NotADirectoryError("The root directory must be an existing directory")

        self.token = bytes(token, 'utf-8')

        if file_size_limit <=0:
            raise ValueError("The file size limit must be greater than 0")
        self.file_size_limit = file_size_limit

        if min_chunk_size <=0:
            raise ValueError("The minimum chunk size must be greater than 0")

        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        self.state = ServerState.IDLE

        # server UPLOAD and DOWNLOAD state related attributes
        self.chunk_size       = 0
        self.temporary_file   = None # file open in 'wb' mode OR file open in 'rb' mode
        self.file_description = None
        self.remaining_bytes  = 0
        self.file_destination = None # upload only attribute

        # socket relate attributes
        self.router = None
        self.dealer = None
        self.socket = None

        self.is_running = False

    def initialize_sockets(self, context):
        self.router = context.socket(zmq.ROUTER)
        self.router.bind(self.router_address)

        #self.router.setsockopt(zmq.CURVE_SECRETKEY, private_key)

        self.dealer = context.socket(zmq.DEALER)
        self.dealer.bind(self.socket_address)

        self.socket = context.socket(zmq.REP)
        self.socket.connect(self.socket_address)

    def terminate_sockets(self):
        self.socket.disconnect(self.socket_address)
        self.dealer.unbind(self.socket_address)
        self.router.unbind(self.router_address)

    def initiate_upload_file(self, file_path, file_size, chunk_size):
        # create temporary file to write
        self.file_descriptor, filename = mkstemp()
        self.temporary_file = open(filename, 'wb')

        self.file_destination = os.fspath(file_path)

        # initialize remaining bytes counter
        self.chunk_size      = chunk_size
        self.remaining_bytes = file_size

        # put server to UPLOAD state
        self.state = ServerState.UPLOAD

    def terminate_upload_file(self):
        # finalize the temporary file and move it to actual destination
        filename = self.temporary_file.name

        self.temporary_file.close()
        shutil.move(filename, self.file_destination)

        # close temporary file descriptor
        os.close(self.file_descriptor)

        self.temporary_file   = None
        self.file_description = None

        # reset chunk size attribute to 0
        self.chunk_size = 0

        # reset other UPLOAD state related attributes
        self.remaining_bytes  = 0
        self.file_destination = None

        # put server back to IDLE state
        self.state = ServerState.IDLE

    def cancel_upload_file(self):
        # close and delete temporary file
        self.temporary_file.close()
        os.close(self.file_descriptor)

        self.temporary_file   = None
        self.file_description = None

        # reset chunk size attribute to 0
        self.chunk_size = 0

        # reset other UPLOAD state related attributes
        self.remaining_bytes  = 0
        self.file_destination = None

        # put server back to IDLE state
        self.state = ServerState.IDLE

    def initiate_download_file(self, file_path, file_size, chunk_size):
        # create temporary file
        self.temporary_file = file_path.open('rb')

        ## initialize remaining bytes counter
        self.chunk_size      = chunk_size
        self.remaining_bytes = file_size

        # put server to DOWNLOAD state
        self.state = ServerState.DOWNLOAD

    def terminate_download_file(self):
        # close and delete temporary file
        self.temporary_file.close()
        self.temporary_file = None

        # reset chunk size attribute to 0
        self.chunk_size = 0

        # reset other DOWNLOAD state related attributes
        self.remaining_bytes = 0

        # put server back to IDLE state
        self.state = ServerState.IDLE

    def cancel_download_file(self):
        # close and delete temporary file
        self.temporary_file.close()
        self.temporary_file = None

        # reset chunk size attribute to 0
        self.chunk_size = 0

        # reset other DOWNLOAD state related attributes
        self.remaining_bytes = 0

        # put server back to IDLE state
        self.state = ServerState.IDLE

    def run(self, hostname, port):
        # initialize sockets (router, dealer and socket)
        context = zmq.Context.instance()

        self.router_address = 'tcp://{0}:{1}'.format(hostname, str(port))
        self.socket_address = 'inproc://socket'

        self.initialize_sockets(context)

        # start the main loop
        self.is_running = True
        self.loop()

        # terminate sockets (router, dealer and socket)
        self.terminate_sockets()

    def process_router(self):
        # read incoming messages from router sockets and reroute them to
        # the dealer if the token (socket identity) is valid
        try:
            identity, frame, message = self.router.recv_multipart(zmq.DONTWAIT)
        except zmq.Again:
            return

        if identity == self.token:
            self.dealer.send_multipart([identity, frame, message])

    def process_list_files_request(self, request):
        """ Process LIST_FILES request.

        The request is expected to contain the directory for which the
        server must list files for.

        The possible responses are.

        * ACCEPTED with FILES_LISTED and the list of files, if the listing was successful
        * REFUSED with NOT_A_DIRECTORY if the list files directory doesn't exists

        Other responsed include ERROR with BAD_REQUEST if the request is
        imporperly formatted, or ERROR with UNKNOWN ERROR if any other
        error occured during the reading of the directory.
        """

        # extract list directory from request, raise bad request error
        # if something goes wrong
        try:
            assert isinstance(request, tuple)
            assert len(request) == 2

            directory = PosixPath(request[1])

        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # normalize the directory (later it can be combined with the
        # root directory)
        directory = normalize_directory(directory)

        # combine the list directory with the root directory
        directory = PosixPath(self.root_directory) / directory

        # if the directory doesn't refer to an actual directory, send
        # not a directory refused resonse
        if not directory.exists() or directory.is_file():
            response = make_not_a_directory_response()
            self.socket.send_pyobj(response)

            return

        # build the list of files of the given directory, with files
        # properties
        files_list = []

        for _file in directory.iterdir():
            name          = _file.name
            is_directory  = _file.is_dir()
            size          = _file.stat().st_size
            last_accessed = _file.stat().st_atime

            files_list.append((name, is_directory, size, last_accessed))

        files_list = tuple(files_list)

        # send list file accepted response with list of files
        response = make_files_listed_response(files_list)
        self.socket.send_pyobj(response)

    def process_create_file_request(self, request):
        """ Process CREATE_FILE request.

        The request is expected to contain the name of the file and the
        destination directory.

        The possible responses are.

        * ACCEPTED with FILE_CREATED, if creating the the was successful
        * REFUSED with INVALID_FILE_NAME if a file doesn't have a valid name
        * REFUSED with NOT_A_DIRECTORY if the destination directory doesn't exist
        * REFUSED with FILE_ALREADY_EXISTS if a file (or directory) with that name already exists

        Other responses include ERROR with BAD_REQUEST if the request is
        imporperly formatted, or ERROR with UNKNOWN ERROR if any other
        error occured during the creation of the file.
        """

        # extract name and directory from the request, send bad request
        # error if something goes wrong
        try:
            assert isinstance(request, tuple)
            assert len(request) == 3

            _, name, directory = request
            directory = PosixPath(directory)

        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # return INVALID_FILE_NAME refused response if the file name is
        # not valid
        if not is_file_name_valid(name):
            response = make_invalid_file_name_response()
            self.socket.send_pyobj(response)

            return

        # normalize the directory (later it can be combined with the
        # root directory)
        directory = normalize_directory(directory)

        # combine the destination directory with the root directory
        directory = PosixPath(self.root_directory) / directory

        # return NOT_A_DIRECTORY refused response if the destination
        # isn't an actual directory
        if not directory.exists() or directory.is_file():
            response = make_not_a_directory_response()
            self.socket.send_pyobj(response)

            return

        # combine the destination directory with the name to get the
        # full path of the file to create
        file_path = directory / name

        # return FILE_ALREADY_EXISTS refused response if a file (or
        # directory) with that name already exists
        if file_path.exists():
            response = make_file_already_exists_response()
            self.socket.send_pyobj(response)

            return

        # attempt to create the file and return FILE_CREATED unless an
        # error occured
        try:
            file_path.touch()
        except Exception as error:
            response = make_unknown_error_response(str(error))
        else:
            response = make_file_created_response()

        self.socket.send_pyobj(response)

    def process_make_directory_request(self, request):
        """ Process MAKE_DIRECTORY request.

        The request is expected to contain the destination directory,
        and the name of the directory to create.

        The possible responses are.

        * ACCEPTED with DIRECTORY_CREATED
        * REFUSED with INVALID_FILE_NAME
        * REFUSED with NOT_A_DIRECTORY
        * REFUSED with FILE_ALREADY_EXISTS

        Other responses include ERROR with BAD_REQUEST or UNKNOWN ERROR.
        """

        # extract directory and name from the request, send bad request
        # error if something goes wrong
        try:
            assert isinstance(request, tuple)
            assert len(request) == 3

            _, name, directory = request
            directory = PosixPath(directory)

        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # return INVALID_FILE_NAME refused response if the directory
        # name is not valid
        if not is_file_name_valid(name):
            response = make_invalid_file_name_response()
            self.socket.send_pyobj(response)

            return

        # normalize the directory (later it can be combined with the
        # root directory)
        directory = normalize_directory(directory)

        # combine the destination directory with the root directory
        directory = PosixPath(self.root_directory) / directory

        # return NOT_A_DIRECTORY refused response if the destination
        # isn't an actual directory
        if not directory.exists() or directory.is_file():
            response = make_not_a_directory_response()
            self.socket.send_pyobj(response)

            return

        # combine the destination directory with the name to get the
        # full path of the directory to create
        directory_path = directory / name

        # return FILE_ALREADY_EXISTS refused response if the a directory
        # (or a file) with that name already exists
        if directory_path.exists():
            response = make_file_already_exists_response()
            self.socket.send_pyobj(response)

            return

        # attempt to create the directory and return DIRECTORY_CREATED
        # unless an error occured
        try:
            directory_path.mkdir()
        except Exception as error:
            response = make_unknown_error_response(str(error))
        else:
            response = make_directory_created_response()

        self.socket.send_pyobj(response)

    def process_upload_file_chunk_request(self, request):
        """ Process SEND_CHUNK request.

        The possible responses are.

        * ACCEPTED with CHUNK_ACCEPTED
        * ACCEPTED with TRANSFER_COMPLETED
        * REFUSED with INVALID_FILE_NAME

        Long description.
        """

        # extract chunk data from the request and send bad request
        # error if something goes wrong
        try:
            assert isinstance(request, tuple)
            assert len(request) == 2

            chunk_data = request[1]
            assert isinstance(chunk_data, bytes)

        except Exception:
            self.cancel_upload_file()

            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # chunk data size must be equal to initial chunk size or equal
        # to the remaining bytes (and of course greater than 0)
        try:
            assert len(chunk_data) != 0

            if self.remaining_bytes <= self.chunk_size:
                assert len(chunk_data) == self.remaining_bytes
            else:
                assert len(chunk_data) == self.chunk_size

        except AssertionError:
            self.cancel_upload_file()

            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # write the chunk data to the temporary file, and update the
        # remaining bytes counter
        self.temporary_file.write(chunk_data)
        self.remaining_bytes -= len(chunk_data)

        assert self.remaining_bytes >= 0

        # send chunk accepted response, unless the transfer is
        # terminated, in which case transfer completed is sent instead
        if self.remaining_bytes == 0:
            self.terminate_upload_file()
            response = make_transfer_completed_response()
        else:
            response = make_chunk_received_response()

        self.socket.send_pyobj(response)

    def process_upload_file_cancel_request(self, request):
        """ Process CANCEL_TRANSFER request.

        The only possible response is to accepting the request. Clean
        up server states and put it back to IDLE mode.
        """

        self.cancel_upload_file()

        # send ACCEPTED response (only possible response)
        response = make_transfer_cancelled_response()
        self.socket.send_pyobj(response)

    def process_upload_file_requests(self, request):
        """ Process upload file releated requests.

        Read any incoming requests when server is in UPLOAD state. If
        the request can't be read, a bad request error is sent.

        In UPLOAD mode, the server expects one of the following request.

           * SEND_CHUNK
           * CANCEL_TRANSFER

        Any other type of request results in a bad request error.
        """

        try:
            assert isinstance(request, tuple)
            request_type = request[0]
        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)
        else:
            if request_type == Request.SEND_CHUNK:
                self.process_upload_file_chunk_request(request)
            elif request_type == Request.CANCEL_TRANSFER:
                self.process_upload_file_cancel_request(request)
            else:
                response = make_bad_request_error()
                self.socket.send_pyobj(response)

    def process_upload_file_request(self, request):
        """ Process UPLOAD_FILE request.

        The request is expected to contain the name of the uploaded
        file, its destination directory, its size and the chunk size.

        The possible responses are.

        * ACCEPTED with TRANSFER_ACCEPTED
        * REFUSED  with INCORRECT_FILE_SIZE
        * REFUSED  with INCORRECT_CHUNK_SIZE
        * REFUSED  with INVALID_FILE_NAME
        * REFUSED with NOT_A_DIRECTORY
        * REFUSED with FILE_ALREADY_EXISTS

        Other responses include ERROR with BAD_REQUEST or UNKNOWN ERROR.
        """

        # extract informtion from request and trigger bad request error
        # if something goes wrong
        try:
            assert isinstance(request, tuple)
            assert len(request) == 5

            _, name, directory, file_size, chunk_size = request
            directory = PosixPath(directory)

        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # check if file size and chunk size are correct, send refused
        # response and fail early if this is the case
        if file_size <= 0 or file_size >= self.file_size_limit:
            response = make_incorrect_file_size_response()
            self.socket.send_pyobj(response)

            return

        if chunk_size < self.min_chunk_size or chunk_size > self.max_chunk_size:
            response = make_incorrect_chunk_size_response()
            self.socket.send_pyobj(response)

            return

        # return INVALID_FILE_NAME refused response if the upload file
        # name isn't valid
        if not is_file_name_valid(name):
            response = make_invalid_file_name_response()
            self.socket.send_pyobj(response)

            return

        # normalize the directory (later it can be combined with the
        # root directory)
        directory = normalize_directory(directory)

        # combine the destination directory with the root directory
        directory = PosixPath(self.root_directory) / directory

        if not directory.exists() or directory.is_file():
            response = make_not_a_directory_response()
            self.socket.send_pyobj(response)

            return

        # combine the destination directory with the name to get the
        # full path of the upload file
        file_path = directory / name

        # check if file doesn't already exists
        if file_path.exists():
            response = make_file_already_exists_response()
            self.socket.send_pyobj(response)

            return

        # upload file request is accepted, initiate the upload
        # process
        try:
            self.initiate_upload_file(file_path, file_size, chunk_size)
        except Exception as error:
            response = make_unknown_error_response(str(error))
        else:
            # todo: adjust the actual chunk size
            response = make_transfer_accepted_response()

        self.socket.send_pyobj(response)

    def process_download_file_chunk_request(self, request):
        """ Process RECEIVE_CHUNK request.

        The possible responses are.

        * ACCEPTED with CHUNK_SENT
        * ACCEPTED with TRANSFER_COMPLETED

        * REFUSED with INVALID_FILE_NAME

        Long description.
        """

        ## chunk data size must be equal to initial chunk size or equal
        ## to the remaining bytes (and of course greater than 0)
        #try:
            #assert len(chunk_data) != 0

            #if self.remaining_bytes <= self.chunk_size:
                #assert len(chunk_data) == self.remaining_bytes
            #else:
                #assert len(chunk_data) == self.chunk_size

        #except AssertionError:
            #self.cancel_upload_file()

            #response = make_bad_request_error()
            #self.socket.send_pyobj(response)

            #return

        ## write the chunk data to the temporary file, and update the
        ## remaining bytes counter
        #self.temporary_file.write(chunk_data)
        #self.remaining_bytes -= len(chunk_data)

        #assert self.remaining_bytes >= 0

        ## send chunk accepted response, unless the transfer is
        ## terminated, in which case transfer completed is sent instead
        #if self.remaining_bytes == 0:
            #self.terminate_upload_file()
            #response = make_transfer_completed_response()
        #else:
            #response = make_chunk_received_response()

        #self.socket.send_pyobj(response)

        # read the chunk data to the temporary file, and update the
        # remaining bytes counter
        chunk_data = self.temporary_file.read(self.chunk_size)

        self.remaining_bytes -= len(chunk_data)
        assert self.remaining_bytes >= 0

        if self.remaining_bytes > 0:
            response = make_chunk_sent_response(chunk_data)
        else:
            response = make_transfer_completed_response(chunk_data)

        self.socket.send_pyobj(response)

    def process_download_file_cancel_request(self, request):
        """ Process CANCEL_TRANSFER request.

        The only possible response is to accepting the request. Clean
        up server states and put it back to IDLE mode.
        """

        self.cancel_download_file()

        # send ACCEPTED response (only possible response)
        response = make_transfer_cancelled_response()
        self.socket.send_pyobj(response)

    def process_download_file_requests(self, request):
        """ Process download file releated requests.

        Read any incoming requests when server is in DOWNLOAD state. If
        the request can't be read, a bad request error is sent.

        In DOWNLOAD mode, the server expects one of the following
        request.

           * RECEIVE_CHUNK
           * CANCEL_TRANSFER

        Any other type of request results in a bad request error.
        """

        try:
            assert isinstance(request, tuple)
            request_type = request[0]
        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)
        else:
            if request_type == Request.RECEIVE_CHUNK:
                self.process_download_file_chunk_request(request)
            elif request_type == Request.CANCEL_TRANSFER:
                self.process_download_file_cancel_request(request)
            else:
                response = make_bad_request_error()
                self.socket.send_pyobj(response)

    def process_download_file_request(self, request):
        """ Process DOWNLOAD_FILE request.

        The possible response are.

        - REFUSED with INCORRECT_CHUNK_SIZE
        - REFUSED with INVALID_FILE_NAME

        - REFUSED with NOT_A_DIRECTORY

        - REFUSED with FILE_NOT_FOUND
        - REFUSED with NOT_A_FILE

        - ACCEPTED with TRANSFER_ACCEPTED

        - REFUSED with NOT_A_DIRECTORY if the file directory doesn't exists.
        - REFUSED with INCORRECT_CHUNK_SIZE if the chunk size isnn' t accepted.

        Long descripion.
        """

        # extract information from request and trigger bad request error
        # if something goes wrong
        try:
            assert isinstance(request, tuple)
            assert len(request) == 4

            _, name, directory, chunk_size = request
            directory = PosixPath(directory)

        except Exception:
            response = make_bad_request_error()
            self.socket.send_pyobj(response)

            return

        # check if chunk size are correct, send refused response and
        # fail early if this is the case
        if chunk_size < MINIMUM_CHUNK_SIZE or chunk_size > MAXIMUM_CHUNK_SIZE:
            response = make_incorrect_chunk_size_response()
            self.socket.send_pyobj(response)

            return

        # return INVALID_FILE_NAME refused response if the download file
        # name isn't valid
        if not is_file_name_valid(name):
            response = make_invalid_file_name_response()
            self.socket.send_pyobj(response)

            return

        # normalize the directory (later it can be combined with the
        # root directory)
        directory = normalize_directory(directory)

        # combine the source directory with the root directory
        directory = PosixPath(self.root_directory) / directory

        # send NOT_A_DIRECTORY
        if not directory.exists() or not directory.is_dir():
            response = make_not_a_directory_response()
            self.socket.send_pyobj(response)

            return

        # combine the source directory with the name to get the full
        # path of the download file
        file_path = directory / name

        # send FILE_NOT_FOUND
        if not file_path.exists():
            response = make_file_not_found_response()
            self.socket.send_pyobj(response)

            return

        # send NOT_A_FILE
        if not file_path.is_file():
            response = make_not_a_file_response()
            self.socket.send_pyobj(response)

            return

        # compute file size
        source_file = file_path.open('rb')
        source_file.seek(0, os.SEEK_END)
        file_size = source_file.tell()
        source_file.seek(0, os.SEEK_SET)
        source_file.close()

        # download file request is accepted, initiate the download
        # process
        try:
            self.initiate_download_file(file_path, file_size, chunk_size)
        except Exception as error:
            response = make_unknown_error_response(str(error))
        else:
            response = make_transfer_accepted_response(file_size)

        self.socket.send_pyobj(response)

    def process_remove_file_request(self, request):
        """ Process REMOVE_FILE request.

        Long description here.
        """

        raise NotImplementedError

    def process_socket(self):
        """ Process socket incoming requests.

        Read any incoming requests and dispatch it according to server
        state and request type. If the request can't be read, a bad
        request error is sent.

        In IDLE mode, the server expects one of the following request.

           * LIST_FILES
           * CREATE_FILE
           * MAKE_DIRECTORY
           * UPLOAD_FILE
           * DOWNLOAD_FILE
           * REMOVE_FILE

        Any other type of request results in a bad request error.
        """

        try:
            request = self.socket.recv_pyobj(zmq.DONTWAIT)
        except zmq.Again:
            return

        if self.state == ServerState.UPLOAD:
            self.process_upload_file_requests(request)
        elif self.state == ServerState.DOWNLOAD:
            self.process_download_file_requests(request)
        else:
            try:
                assert isinstance(request, tuple)
                request_type = request[0]
            except Exception:
                response = make_bad_request_error()
                self.socket.send_pyobj(response)
            else:
                if request_type == Request.LIST_FILES:
                    self.process_list_files_request(request)
                elif request_type == Request.CREATE_FILE:
                    self.process_create_file_request(request)
                elif request_type == Request.MAKE_DIRECTORY:
                    self.process_make_directory_request(request)
                elif request_type == Request.UPLOAD_FILE:
                    self.process_upload_file_request(request)
                elif request_type == Request.DOWNLOAD_FILE:
                    self.process_download_file_request(request)
                elif request_type == Request.REMOVE_FILE:
                    self.process_remove_file_request(request)
                else:
                    response = make_bad_request_error()
                    self.socket.send_pyobj(response)

    def process_dealer(self):
        # read dealer socket messages and send them back to the router
        try:
            identity, frame, message = self.dealer.recv_multipart(zmq.DONTWAIT)
        except zmq.Again:
            pass
        else:
            self.router.send_multipart([identity, frame, message])

    def loop(self):

        while self.is_running:
            self.process_router()
            self.process_socket()
            self.process_dealer()

    def terminate(self):
        self.is_running = False
