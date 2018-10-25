# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
from pathlib import PosixPath, PurePosixPath
import zmq
from remofile.protocol import *
from remofile.exceptions import *

CHUNK_SIZE = 4096

class Client:
    """ Remofile client.

    This class implements the client side of Remofile that behaves
    according to the protocol.

    It's a synchronous (non-threaded) and "connectionless" interface to
    interact with the remote directory. Indeed, a connection is
    etablished behind the scene but it isn't exposed. As a result, it
    simplifies the interface and you don't have do deal directly with
    connections (and eventual re-connections that may happen). Instead,
    you use a timeout and catch the :py:exc:`TimeoutError` exception
    that is raised if the time is out. All production code should use a
    timeout.

    All native file operations are implemented such as listing files,
    creating files and directories, upload/download files and deleting
    files. Exceptions are raised whenever errors occur or if the file
    operation couldn't be successfully completed. Also note that
    directories and symbolic links are also reffered as 'file'.

    For more complex file operations such as synchronizing directories
    or upload/download trees of files, while handling file conflicts and
    glob pattern, see the algorithm module. Otherwise implement your
    file operations on top of the client instance.
    """

    def __init__(self, hostname, port, token):
        """ Construct a :py:class:`Client` instance.

        The client instance is constructed from the hostname (which can
        either be "localhost" or any valid IP), the port and the token.

        The token should be generated with the :py:func:`generate_token()`
        to ensure validity of its value, or a :py:exc:`ValueError`
        exception is raised.

        :param str hostname: The server IP address (can be "localhost").
        :param int port:     The server port.
        :param str token:    The token to use for authentication.
        :raises ValueError:  If the token isn't valid.
        """

        context = zmq.Context()

        self.socket_address = 'tcp://{0}:{1}'.format(hostname, str(port))

        self.socket = context.socket(zmq.REQ)

        try:
            self.token = bytes(token, 'utf-8')
            self.socket.setsockopt(zmq.IDENTITY, self.token)
        except Exception:
            raise ValueError("the token is not valid")

        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.socket_address)

    def __del__(self):
        self.socket.disconnect(self.socket_address)

    def list_files(self, directory, timeout=None):
        """ List files in the remote directory.

        It lists files of a given directory in a remote directory and
        returns a dictionnary associating file names with their
        metadata. The metadata is a tuple that includes a boolean
        indicating whether the file is a directory or not, the size of
        the file (the value is 0 in case of directory) and the last
        modification time of the file.

        Return value example. ::

            {
                'foo.bin' : (False, 423, 4687421324),
                'bar'     : (True, 0, 1654646515)
            }

        The directory parameter must be a :term:`path-like object` that
        refers to an **existing** directory in the remote directory for
        which it must list files for. If the directory doesn't exist,
        the :py:exc:`FileNotFoundErrror` exception is raised, and if
        it's not an actual directory, the :py:exc:`NotADirectoryError`
        exception is raised. It must be an absolute path or a
        :py:exc:`ValueError` exception is raised.

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param path directory:      The given remote directory to list files for.
        :param int timeout:         How many milliseconds to wait before giving up
        :raises ValueError:         If the directory is not an absolute path.
        :raises FileNotFoundError:  If the directory doesn't exist.
        :raises NotADirectoryError: If the directory is not a directory.
        :raises TimeoutError:       If it takes more than the timeout value to receive a response.
        :return: A dictionnary associating file name with their metadata.
        :rtype: dict
        """

        # ensure we work with a posix path
        directory = PurePosixPath(directory)

        # raise ValueError exception if the directory is not an
        # absolute path
        if not directory.is_absolute():
            raise ValueError("Directory must be an absolute path")

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
            if response[1] == Reason.FILE_NOT_FOUND:
                raise FileNotFoundError
            if response[1] == Reason.NOT_A_DIRECTORY:
                raise NotADirectoryError
            else:
                raise NotImplementedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

        raise NotImplementedError

    def create_file(self, name, directory, timeout=None):
        """ Create a file in the remote directory.

        It creates an empty file with a given name in a given directory
        located in the remote directory.

        The name parameter must be a string of a :term:`valid file
        name` and must not conflict with an existing file (or directory)
        in the given remote directory. If the name isn't valid, a
        :py:exc:`FileNameError` is raised and if the file is
        conflicting, a :py:exc:`FileExistsError` exception is raised.

        The directory parameter must be a :term:`path-like object` that
        refers to an **existing** directory in the remote directory
        where the file must be created. If the directory doesn't exist,
        the :py:exc:`FileNotFoundError` exception is raised, and if
        it's not an actual directory, the :py:exc:`NotADirectoryError`
        exception is raised. It must be an absolute path or a
        :py:exc:`ValueError` exception is raised.

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param str name:            The name of the file to create.
        :param path directory:      The given remote directory where to create the file.
        :param int timeout:         How many milliseconds to wait before giving up
        :raises ValueError:         If the directory is not an absolute path.
        :raises FileNotFound:       If the directory doesn't exist.
        :raises NotADirectoryError  If the directory is not a directory.
        :raises FileNameError:      If the name of the file isn't valid.
        :raises FileExistsError:    If the name conflicts with the name of an existing file or directory.
        :raises TimeoutError:       If it takes more than the timeout value to receive a response.
        """

        # ensure we work with a posix path
        directory = PurePosixPath(directory)

        # raise ValueError exception if the directory is not an
        # absolute path
        if not directory.is_absolute():
            raise ValueError("Directory must be an absolute path")

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
                raise FileNameError
            elif reason_type == Reason.FILE_NOT_FOUND:
                raise FileNotFoundError
            elif reason_type == Reason.NOT_A_DIRECTORY:
                raise NotADirectoryError
            elif reason_type == Reason.FILE_ALREADY_EXISTS:
                raise FileExistsError
            else:
                raise NotImplementedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

    def make_directory(self, name, directory, timeout=None):
        """ Create a directory in the remote directory.

        It creates an empty directory with a given name in a given
        directory located in the remote directory.

        The name parameter must be a string of a :term:`valid file
        name` and must not conflict with an existing file (or directory)
        in the given remote directory. If the name isn't valid, a
        :py:exc:`FileNameError` is raised and if the file is
        conflicting, a :py:exc:`FileExistsError` exception is raised.

        The directory parameter must be a :term:`path-like object` that
        refers to an **existing** directory in the remote directory
        where the directory must be created. If the directory doesn't
        exist, the :py:exc:`NotADirectoryError` exception is raised, and
        if it's not an actual directory, the :py:exc:`NotADirectoryError`
        exception is raised. It must be an absolute path or a
        :py:exc:`ValueError` exception is raised.

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param str name:            The name of the file to create.
        :param path directory:      The given remote directory where to create the file.
        :param int timeout:         How many milliseconds to wait before giving up
        :raises ValueError:         If the directory is not an absolute path.
        :raises FileNotFound:       If the directory doesn't exist.
        :raises NotADirectoryError  If the directory is not a directory.
        :raises FileNameError:      If the name isn't valid.
        :raises FileExistsError:    If the name conflicts with the name of an existing file or directory.
        :raises TimeoutError:       If it takes more than the timeout value to receive a response.
        """

        # ensure we work with a posix path
        directory = PurePosixPath(directory)

        # raise ValueError exception if the directory is not an
        # absolute path
        if not directory.is_absolute():
            raise ValueError("Directory must be an absolute path")

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
            if reason_type == Reason.INVALID_FILE_NAME:
                raise FileNameError
            elif reason_type == Reason.FILE_NOT_FOUND:
                raise FileNotFoundError
            elif reason_type == Reason.NOT_A_DIRECTORY:
                raise NotADirectoryError
            elif reason_type == Reason.FILE_ALREADY_EXISTS:
                raise FileExistsError
            else:
                raise NotImplementedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

    def upload_file(self, source, destination, name=None, chunk_size=512,
        process_chunk=None, timeout=None):
        """ Upload a file to the remote directory.

        This method uploads a single file to a given directory in the
        remote directory.

        The **source** parameter refers to the local file to be
        transfered to the remote directory and must to be a
        :term:`path-like object`. If it's a relative path, it's treated
        like relative to the current working directory. If the source
        file can't be found or is not a file, the :py:exc:`SourceNotFound`
        exception is raised.

        The **destination** parameter refers to the remote directory in
        which the file must be transfered to. It must be a
        :term:`path-like object` of an **existing** directory and it
        must be an absolute path or the :py:exc:`ValueError` exception
        is raised. If the destination directory can't be found or is not
        a directory, the :py:exc:`DestinationNotFound` exception is
        raised.

        The name parameter can be used to rename the source file while
        uploading it (the content is guaranteed to be the same). It must
        be a string of a :term:`valid file name` and must not conflict
        with an existing file (or directory) in the destination
        directory. By default, it reads the name from the source to
        leave it unchanged. If the name isn't valid, a
        :py:exc:`FileNameError` is raised and if the file is
        conflicting, a :py:exc:`FileExistsError` exception is raised.

        Additionally, you can adjust the chunk size value which defines
        how fragmented the file has to be sent to the server and/or pass
        a callback that process each fragment **before** it's sent to
        the server. Usually, the chunk value is between 512 and 8192.

        The callback is called with various parameters and in a
        specific order; the chunk data, the remaining bytes, the file
        size and the file name. The chunk data is a bytes string of the
        actual data about to be sent to the server. The remaining bytes
        is an integer indicating the number of bytes left to be sent
        (and this includes the current chunk of data). The file size is
        a fixed integer telling how large the file is, and the file name
        is the file name currently being processed.

        For instance, it can be used to display a progress indicator.
        Here is an example. ::

            def display_progress(chunk_data, remaining_bytes, file_size, file_name):
                chunk_size = 512
                progress = (file_size - (remaining_bytes - len(chunk_data))) / file_size * 100

                sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, file_name))
                sys.stdout.flush()

                if remaining_bytes <= chunk_size:
                    sys.stdout.write('\n')

                return True

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param source:        The (local) source file to upload.
        :param destination:   The (remote) destination directory where to upload the file.
        :param name:          The name of the file after it's uploaded.
        :param chunk_size:    How fragmented (in bytes) the file is during the upload process.
        :param process_chunk: Function processing chunks before they are sent out.
        :param timeout:       How many milliseconds to wait before giving up.
        :raises ValueError:          If the destination directory isn't an absolute path.
        :raises SourceNotFound:      If the source file doesn't exist or isn't a file.
        :raises DestinationNotFound: If the destination directory doesn't exist or isn't a directory.
        :raises FileExistsError:     If the source file conflicts with an existing file or directory.
        :raises FileNameError:       If the source file doesn't have a valid name.
        :raises ValueError:          If the chunk size or file size is invalid.
        :raises TimeoutError:        If it takes more than the timeout value to receive a response.
        """

        # ensure we work with posix paths
        source = PosixPath(source)
        destination = PurePosixPath(destination)

        # normalize the source to work with an absolute path
        if not source.is_absolute():
            source = PosixPath(os.getcwd(), source)

        # compute the name from the source if not specified (file name
        # unchanged)
        if not name:
            name = source.name

        # raise SourceNotFound exception if the source file doesn't
        # exist or is not a file
        if not source.exists() or not source.is_file():
            raise SourceNotFound("Source file could not be found")

        # raise ValueError exception if destination directory is not an
        # absolute path
        if not destination.is_absolute():
            raise ValueError("Destination must be an absolute path")

        # check if the destination directory exists and raises
        # DestinationNotFound exception if it doesn't exist or is not
        # a directory (a root is always a valid destination)
        if str(destination) != destination.root:
            try:
                files = self.list_files(destination.parent, timeout)
            except (FileNotFoundError, NotADirectoryError):
                raise DestinationNotFound("Destination directory could not be found")

            if destination.name not in files or files[destination.name][0] == False:
                raise DestinationNotFound("Destination directory could not be found")

        # check if the file name doesn't conflict with an existing file
        # (or directory) in the destination directory
        files = self.list_files(destination, timeout)

        if name in files:
            raise FileExistsError

        # initiate and do the upload process, will raise FileNameError
        # exception if the file name is invalid, and a ValueError if
        # either the chunk size or the file size limit is incorrects
        self._upload_file(source, destination, name, chunk_size, process_chunk, timeout)

    def upload_directory(self, source, destination, name=None,
        chunk_size=512, process_chunk=None, timeout=None):
        """ Upload a directory to the remote directory.

        This method uploads an entire directory to a given directory in
        the remote directory.

        The **source** parameter refers to the local directory to be
        transfered to the remote directory and must to be a
        :term:`path-like object`. If it's a relative path, it's treated
        like relative to the current working directory. If the source
        directory can't be found or is not a directory, the
        :py:exc:`SourceNotFound` exception is raised.

        The **destination** parameter refers to the remote directory in
        which the directory must be transfered to. It must be a
        :term:`path-like object` of an **existing** directory and it
        must be an absolute path or the :py:exc:`ValueError` exception
        is raised. If the destination directory can't be found or is
        not a directory, the :py:exc:`DestinationNotFound` exception is
        raised.

        The name parameter can be used to rename the source directory
        while uploading it (the content is guaranteed to be the same).
        It must be a string of a :term:`valid file name` and must not
        conflict with an existing directory (or file) in the destination
        directory. By default, it reads the name from the source to
        leave it unchanged. If the name isn't valid, a
        :py:exc:`FileNameError` is raised and if the file is
        conflicting, a :py:exc:`FileExistsError` exception is raised.

        Additionally, you can adjust the chunk size value which defines
        how fragmented files have to be sent to the server and/or pass
        a callback that process each fragment **before** it's sent to
        the server. Usually, the chunk value is between 512 and 8192.

        The callback is called with various parameters and in a
        specific order; the chunk data, the remaining bytes, the file
        size and the file name. The chunk data is a bytes string of the
        actual data about to be sent to the server. The remaining bytes
        is an integer indicating the number of bytes left to be sent
        (and this includes the current chunk of data). The file size is
        a fixed integer telling how large the file is, and the file name
        is the file name currently being processed.

        For instance, it can be used to display a progress indicator.
        Here is an example. ::

            def display_progress(chunk_data, remaining_bytes, file_size, file_name):
                chunk_size = 512
                progress = (file_size - (remaining_bytes - len(chunk_data))) / file_size * 100

                sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, file_name))
                sys.stdout.flush()

                if remaining_bytes <= chunk_size:
                    sys.stdout.write('\n')

                return True

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param source:        The (local) source directory to upload.
        :param destination:   The (remote) destination directory where to upload the directory.
        :param name:          The name of the directory after it's uploaded.
        :param chunk_size:    How fragmented (in bytes) files are during the upload process.
        :param process_chunk: Function processing chunks before they are sent out.
        :param timeout:       How many milliseconds to wait before giving up.
        :raises ValueError:          If the destination directory isn't an absolute path.
        :raises SourceNotFound:      If the source directory doesn't exist or isn't a directory.
        :raises DestinationNotFound: If the destination directory doesn't exist or isn't a directory.
        :raises FileExistsError:     If the source directory conflicts with an existing file or directory.
        :raises FileNameError:       If the source directory doesn't have a valid name.
        :raises ValueError:          If the chunk size or file size is invalid.
        :raises TimeoutError:        If it takes more than the timeout value to receive a response.
        """

        # ensure we work with posix paths
        source = PosixPath(source)
        destination = PurePosixPath(destination)

        # normalize the source to work with an absolute path
        if not source.is_absolute():
            source = PosixPath(os.getcwd(), source)

        # compute the name from the source if not specified (directory
        # name unchanged)
        if not name:
            name = source.name

        # raise SourceNotFound exception if the source directory doesn't
        # exist or is not a directory
        if not source.exists() or not source.is_dir():
            raise SourceNotFound("Source directory could not be found")

        # raise ValueError exception if destination directory is not an
        # absolute path
        if not destination.is_absolute():
            raise ValueError("Destination must be an absolute path")

        # check if the destination directory exists and raises
        # DestinationNotFound exception if it doesn't exist or is not
        # a directory (a root is always a valid destination)
        if str(destination) != destination.root:
            try:
                files = self.list_files(destination.parent, timeout)
            except (FileNotFoundError, NotADirectoryError) as error:
                raise DestinationNotFound("Destination directory could not be found")

            if destination.name not in files or files[destination.name][0] == False:
                raise DestinationNotFound("Destination directory could not be found")

        # check if the directory name doesn't conflict with an existing
        # directory (or file) in the destination directory
        files = self.list_files(destination, timeout)

        if name in files:
            raise FileExistsError

        # the following code is a workaround! it should let the server
        # refuse the chunk size instead, but if we do that, the
        # first directory is created first and left undeleted after the
        # first file is denied from being uploaded
        if chunk_size == 0 or chunk_size > 8192:
            raise ValueError("Chunk size value is invalid")

        # initiate and do the upload process, will raise FileNameError
        # exception if of the file in the direcotry has an invalid name,
        # and a ValueError if either the chunk size or the file size
        # limit is incorrect
        self._upload_directory(source, destination, name, chunk_size, process_chunk, timeout)

    def download_file(self, source, destination, name=None, chunk_size=512,
        process_chunk=None, timeout=None):
        """ Download a file from the remote directory.

        This method downloads a single file from a given directory in
        the remote directory.

        The **source** parameter refers to the remote file to be
        transfered from the remote directory and must to be a
        :term:`path-like object`. It must be an absolute path or it will
        raise the ValueError exception. If the source file can't be
        found or is not a file, the SourceNotFound exception is raised.

        The **destination** parameter refers to **an existing** local
        directory in which the file must be transfered to. It must
        be a :term:`path-like object` and if it's a relative path, it's
        treated like relative to the current working directory. If the
        destination directory can't be found or is not a directory, the
        DestinationNotFound exception is raised.

        The name parameter can be used to rename the source file while
        downloading it (the content is guaranteed to be the same). It
        must be a string of a :term:`valid file name` and must not
        conflict with an existing file (or directory) in the destination
        directory. By default, it reads the name from the source to
        leave it unchanged. If the name isn't valid, a
        :py:exc:`FileNameError` is raised and if the file is
        conflicting, a :py:exc:`FileExistsError` exception is raised.

        Additionally, you can adjust the chunk size value which defines
        how fragmented the file has to be received from the server
        and/or pass a callback that process each fragment **before**
        it's written to the local file. Usually, the chunk value is
        between 512 and 8192.

        The callback is called with various parameters and in a
        specific order; the chunk data, the remaining bytes, the file
        size and the file name. The chunk data is a bytes string of the
        actual data just received from the server. The remaining bytes
        is an integer indicating the number of bytes left to be received
        (and this includes the current chunk of data). The file size is
        a fixed integer telling how large the file is, and the file name
        is the file name currently being processed.

        For instance, it can be used to display a progress indicator.
        Here is an example. ::

            def display_progress(chunk_data, remaining_bytes, file_size, file_name):
                chunk_size = 512
                progress = (file_size - (remaining_bytes - len(chunk_data))) / file_size * 100

                sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, file_name))
                sys.stdout.flush()

                if remaining_bytes <= chunk_size:
                    sys.stdout.write('\n')

                return True

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param source:        The (remote) source file to download.
        :param destination:   The (local) destination directory where to download the file.
        :param name:          The name of the file after it's downloaded.
        :param chunk_size:    Foobar.
        :param process_chunk: Foobar.
        :param timeout:       How many milliseconds to wait before giving up.
        :raises ValueError:          If the source directory isn't an absolute path.
        :raises SourceNotFound:      If the source file doesn't exist or isn't a file.
        :raises DestinationNotFound: If the destination directory doesn't exist or isn't a directory.
        :raises FileExistsError:     If the source file conflicts with an existing file or directory.
        :raises FileNameError:       If the source file doesn't have a valid name.
        :raises TimeoutError:        If it takes more than the timeout value to receive a response.
        """

        # ensure we work with posix paths
        source = PurePosixPath(source)
        destination = PosixPath(destination)

        # normalize the destination to work with an absolute path
        if not destination.is_absolute():
            destination = PosixPath(os.getcwd(), destination)

        # compute the name from the source if not specified (file name
        # unchanged)
        if not name:
            name = source.name

        # raise ValueError exception if source directory is not an
        # absolute path
        if not source.is_absolute():
            raise ValueError("Source must be an absolute path")

        # raise SourceNotFound exception if the source file doesn't
        # exist or is not a file
        try:
            files = self.list_files(source.parent, timeout)
        except NotADirectoryError:
            raise SourceNotFound("Source file could not be found")
        except TimeoutError:
            raise TimeoutError
        except Exception:
            raise UnexpectedError

        if source.name not in files or files[source.name][0] == True:
            raise SourceNotFound("Source file could not be found")

        # check if the destination directory exists and raises
        # DestinationNotFound exception if it doesn't exist or is not
        # a directory
        if not destination.exists() or not destination.is_dir():
            raise DestinationNotFound("Destination directory could not be found")

        # check if the file name doesn't conflict with an existing file
        # (or directory) in the destination directory
        if name in os.listdir(destination):
            raise FileExistsError

        # initiate and do the download process
        #try:
        self._download_file(source, destination, name, chunk_size, process_chunk, timeout)
        #except Exception:
            #raise NotImplementedError

    def download_directory(self, source, destination, name=None,
        chunk_size=512, process_chunk=None, timeout=None):
        """ Download a directory from the remote directory.

        This method downloads an entire directory from a given directory
        in the remote directory.

        The **source** parameter refers to the remote directory to be
        transfered from the remote directory and must to be a
        :term:`path-like object`. It must be an absolute path or it will
        raise the ValueError exception. If the source directory can't be
        found or is not a directory, the SourceNotFound exception is
        raised.

        The **destination** parameter refers to **an existing** local
        directory in which the directory must be transfered to. It must
        be a :term:`path-like object` and if it's a relative path, it's
        treated like relative to the current working directory. If the
        destination directory can't be found or is not a directory, the
        DestinationNotFound exception is raised.

        The name parameter can be used to rename the source directory
        while downloading it (the content is guaranteed to be the same).
        It must be a string of a :term:`valid file name` and must not
        conflict with an existing directory (or file) in the destination
        directory. By default, it reads the name from the source to
        leave it unchanged. If the name isn't valid, a
        :py:exc:`FileNameError` is raised and if the file is
        conflicting, a :py:exc:`FileExistsError` exception is raised.

        Additionally, you can adjust the chunk size value which defines
        how fragmented files have to be received from the server and/or
        pass a callback that process each fragment **before** it's
        written to the local file. Usually, the chunk value is
        between 512 and 8192.

        The callback is called with various parameters and in a
        specific order; the chunk data, the remaining bytes, the file
        size and the file name. The chunk data is a bytes string of the
        actual data just received from the server. The remaining bytes
        is an integer indicating the number of bytes left to be received
        (and this includes the current chunk of data). The file size is
        a fixed integer telling how large the file is, and the file name
        is the file name currently being processed.

        For instance, it can be used to display a progress indicator.
        Here is an example. ::

            def display_progress(chunk_data, remaining_bytes, file_size, file_name):
                chunk_size = 512
                progress = (file_size - (remaining_bytes - len(chunk_data))) / file_size * 100

                sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, file_name))
                sys.stdout.flush()

                if remaining_bytes <= chunk_size:
                    sys.stdout.write('\n')

                return True

        If the operation takes longer than the given timeout, a
        :py:exc:`TimeoutError` exception is raised.

        :param source:        The (remote) source directory to download.
        :param destination:   The (local) destination directory where to download the directory.
        :param name:          The name of the directory after it's downloaded.
        :param chunk_size:    Foobar.
        :param process_chunk: Foobar.
        :param timeout:       How many milliseconds to wait before giving up.
        :raises ValueError:          If the source directory isn't an absolute path.
        :raises SourceNotFound:      If the source file doesn't exist or isn't a file.
        :raises DestinationNotFound: If the destination directory doesn't exist or isn't a directory.
        :raises FileExistsError:     If the source file conflicts with an existing file or directory.
        :raises FileNameError:       If the source file doesn't have a valid name.
        :raises TimeoutError:        If it takes more than the timeout value to receive a response.
        """

        # ensure we work with posix paths
        source = PurePosixPath(source)
        destination = PosixPath(destination)

        # normalize the destination to work with an absolute path
        if not destination.is_absolute():
            destination = PosixPath(os.getcwd(), destination)

        # compute the name from the source if not specified (file name
        # unchanged)
        if not name:
            name = source.name

        # raise ValueError exception if source directory is not an
        # absolute path
        if not source.is_absolute():
            raise ValueError("Source must be an absolute path")

        # raise SourceNotFound exception if the source directory doesn't
        # exist or is not a directory
        if str(source) != source.root:
            try:
                files = self.list_files(source.parent, timeout)
            except NotADirectoryError:
                raise SourceNotFound("Source directory could not be found")
            # except TimeoutError: # catch and treat relevant exceptions
            #     raise TimeoutError
            except Exception:
                raise NotImplementedError

            if source.name not in files or files[source.name][0] == True:
                raise SourceNotFound("Source directory could not be found")

        # check if the destination directory exists and raises
        # DestinationNotFound exception if it doesn't exist or is not
        # a directory (a root is always a valid destination)
        if not destination.exists() or not destination.is_dir():
            raise DestinationNotFound("Destination directory could not be found")

        # check if the file name doesn't conflict with an existing file
        # (or directory) in the destination directory
        if name in os.listdir(destination):
            raise FileExistsError

        # the following code is a workaround! it should let the server
        # refuse the chunk size instead, but if we do that, the
        # first directory is created first and left undeleted after the
        # first file is denied from being downloaded
        if chunk_size == 0 or chunk_size > 8192:
            raise ValueError("Chunk size value is invalid")

        # foobars
        self._download_directory(source, destination, name, chunk_size, process_chunk, timeout)


    def delete_file(self, timeout=None):
        """ Delete a file in the remote directory.

        Long description.

        :param timeout: How many milliseconds to wait before giving up
        :type timeout: int
        """

        raise NotImplementedError

    def _upload_file(self, source, destination, name, chunk_size, process_chunk, timeout):
        """ Do upload a file.

        The source and destination parameters are posix paths and their
        validity has previously been checked. The name parameter is the
        name of the file.

        If the chunk size or file size is invalid the ValueError exception is
        raised and if the file name is invalid the FileNameInvalid
        exception is raised. Other exceptions such as BadRequestError,
        CorruptedResponse, UnknownError or UnexpectedError could also
        be raised.

        Exceptions might also be raised by the chunk processing callback
        function.
        """

        # open source file and read its size
        source_file = source.open('rb')
        source_file.seek(0, os.SEEK_END)
        file_size = source_file.tell()
        source_file.seek(0, os.SEEK_SET)

        # if the source file is empty (file size == 0 byte), use create
        # file request instead
        if file_size == 0:
            source_file.close()

            # the three exceptions aren't supposed to be raised because
            # checks have been made earlier, the only exception that
            # should pass is if the file name is invalid, in this case
            # the exception is passed on to the caller
            try:
                self.create_file(name, destination, timeout)
            except (ValueError, NotADirectoryError, FileExistsError) as error:
                raise UnexpectedError(error)

            return

        # initiate upload file process (by sending a UPLOAD_FILE
        # request)
        request = make_upload_file_request(name, destination, file_size, chunk_size)
        self.socket.send_pyobj(request)

        if self.socket.poll(timeout) & zmq.POLLIN:
            response = self.socket.recv_pyobj()
        else:
            raise TimeoutError

        try:
            response_type = response[0]
        except Exception as error:
            raise CorruptedResponse("Unable to extract response type from response", error)

        # handle the three types of response (accepted, refused or
        # error)
        if response_type == Response.ACCEPTED:
            try:
                reason_type = response[1]
            except Exception as error:
                raise CorruptedResponse("Unable to extract reason type from accept response", error)

            try:
                assert reason_type == Reason.TRANSFER_ACCEPTED
            except AssertionError as error:
                raise CorruptedResponse("Invalid reason type in accept response", error)

        elif response_type == Response.REFUSED:
            try:
                reason_type = response[1]
            except Exception as error:
                raise CorruptedResponse("Unable to exract reason type from refuse response", error)

            # the only refused response we expect is an invalid chunk
            # size, an invalid file size or an invalid file name, the
            # others are unexpected errors since previous checks have
            # been made (for instance, we have ensured the file size is
            # greather than 0, and made a create file request instead)
            if reason_type == Reason.INCORRECT_CHUNK_SIZE:
                raise ValueError("Chunk size is invalid")
            elif reason_type == Reason.INVALID_FILE_SIZE:
                raise ValueError("File size limit is invalid")
            elif reason_type == Reason.INVALID_FILE_NAME:
                raise FileNameError
            else:
                raise CorruptedResponse("Invalid reason type in refuse response")

        elif response_type == Response.ERROR:
            self._process_error_response(response)

        # do the upload file process (send data chunks until the upload
        # is completed)
        transfer_completed = False
        last_chunk = False

        while not transfer_completed:
            # compute remaining bytes left to read
            remaining_bytes = file_size - source_file.tell()

            if remaining_bytes <= chunk_size:
                last_chunk = True

            # read next data chunk from the file
            chunk_data = source_file.read(chunk_size)

            # process the chunk with the custom callback (if any) before
            # it's sent out
            if process_chunk:
                try:
                    raise_exception = None
                    should_continue = process_chunk(chunk_data, remaining_bytes, file_size, source.name)
                except Exception as exception:
                    should_continue = False
                    raise_exception = exception

                # if uploading the file should be interrupted, send a
                # CANCEL_TRANSFER request
                if not should_continue:
                    request = make_cancel_transfer_request()
                    self.socket.send_pyobj(request)

                    if self.socket.poll(timeout) & zmq.POLLIN:
                        response = self.socket.recv_pyobj()
                    else:
                        raise TimeoutError

                    try:
                        response_type = response[0]
                    except Exception as error:
                        raise CorruptedResponse("Unable to extract response type from response", error)

                    if response_type == Response.ACCEPTED:
                        try:
                            reason_type = response[1]
                        except Exception as error:
                            raise CorruptedResponse("Unable to extract reason type from accept response", error)

                        try:
                            assert reason_type == Reason.TRANSFER_CANCELLED
                        except AssertionError as error:
                            raise CorruptedResponse("Invalid reason type in accept response", error)

                        if raise_exception:
                            raise raise_exception
                            
                        transfer_completed = True
                        continue

                    elif response_type == Response.ERROR:
                        self._process_error_response(response)
                    else:
                        raise CorruptedResponse("Invalid response type")

            # send data chunk and wait for response
            request = make_send_chunk_request(chunk_data)
            self.socket.send_pyobj(request)

            if self.socket.poll(timeout) & zmq.POLLIN:
                response = self.socket.recv_pyobj()
            else:
                raise TimeoutError

            try:
                response_type = response[0]
            except Exception:
                raise CorruptedResponse("Unable to extract response type from response", error)

            if response_type == Response.ACCEPTED:
                try:
                    reason_type = response[1]
                except Exception as error:
                    raise CorruptedResponse("Unable to extract reason type from accept response", error)

                try:
                    if last_chunk:
                        assert reason_type == Reason.TRANSFER_COMPLETED
                        transfer_completed = True
                    else:
                        assert reason_type == Reason.CHUNK_RECEIVED
                except AssertionError:
                    raise CorruptedResponse("Invalid reason type in accept response")

            elif response_type == Response.ERROR:
                self._process_error_response(response)
            else:
                raise CorruptedResponse("Invalid response type")

        source_file.close()

    def _upload_directory(self, source, destination, name, chunk_size, process_chunk, timeout):
        """ Do upload a directory.

        The source and destination parameters are posix paths and their
        validity has previously been checked. The name parameter is the
        name of the directory.

        If the chunk size or file size is invalid the ValueError
        exception is
        raised and if the file name is invalid the FileNameInvalid
        exception is raised.

        If the chunk size is invalid or if one of the file in the
        diretory has an invalid size, the ValueError exception is
        raised. If the name of the directory or one of the file in the
        directory is invalid, the FileNameInvalid exception is raised.
        Other exceptions such as BadRequestError, CorruptedResponse,
        UnknownError or UnexpectedError could also be raised.

        Exceptions might also be raised by the chunk processing callback
        function.
        """

        # the source is an absolute path pointing to the directory to
        # create in destination
        self.make_directory(name, destination, timeout)

        for source in source.iterdir():
            if source.is_file():
                self._upload_file(source, destination / name, source.name, chunk_size, process_chunk, timeout)
            elif source.is_dir():
                self._upload_directory(source, destination / name, source.name, chunk_size, process_chunk, timeout)
            else:
                raise NotImplementedError

    def _download_file(self, source, destination, name, chunk_size, process_chunk, timeout):
        """ Do download file.

        """

        pass

        ### if the source file is empty (0 byte), use create file request
        ##if file_size  == 0:
            ### TODO: handle exception
            ##self.create_file(name, destination, timeout)
            ##source_file.close()
            ##return

        # initiate download file process
        request = make_download_file_request(source.name, source.parent, chunk_size)
        self.socket.send_pyobj(request)
        response = self.socket.recv_pyobj()

        # process response and raise exceptions if the download request
        # went wrong
        response_type = response[0]

        if response_type == Response.ACCEPTED:
            reason_type = response[1]
            assert reason_type == Reason.TRANSFER_ACCEPTED
            file_size = response[2]
        elif response_type == Response.REFUSED:
            # the only refused response we expect is an invalid chunk
            # size, the others are unexpected errors since previous
            # checks have been made
            reason_type = response[1]

            if reason_type == Reason.INCORRECT_CHUNK_SIZE:
                raise ValueError("Chunk size is invalid")
            else:
                raise UnexpectedError
        elif response_type == Response.ERROR:
            self._process_error_response(response)

        # foobar
        destination_file_path = destination / name
        destination_file = destination_file_path.open('wb')

        # receive data chunks until the download is completed
        transfer_completed = False
        last_chunk = False

        while not transfer_completed:
            # compute remaining bytes left to write
            remaining_bytes = file_size - destination_file.tell()

            if remaining_bytes <= chunk_size:
                last_chunk = True

            # send receive chunk request and wait for response
            request = make_receive_chunk_request()
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
                assert reason_type == Reason.CHUNK_SENT

            chunk_data = response[2]

            # foobar
            if process_chunk:
                should_continue = process_chunk(chunk_data, remaining_bytes, file_size, source.name)

                if not should_continue:
                    request = make_cancel_transfer_request()
                    self.socket.send_pyobj(request)

                    response = self.socket.recv_pyobj()

                    if response[0] != Response.ACCEPTED:
                        raise NotImplementedError

                    assert response[1] == Reason.TRANSFER_CANCELLED

                    transfer_completed = True

                    continue

            # write next data chunk to the file
            destination_file.write(chunk_data)

        destination_file.close()

    def _download_directory(self, source, destination, name, chunk_size, process_chunk, timeout):

        # the source is an absolute path pointing to the directory to
        # create in destination
        os.makedirs(destination / name)

        files_list = self.list_files(source)
        for file_name in files_list.keys():
            is_directory, _, _ = files_list[file_name]

            new_source = source / file_name

            if not is_directory:
                self._download_file(new_source, destination / name, file_name, chunk_size, process_chunk, timeout)
            elif is_directory:
                self._download_directory(new_source, destination / name, file_name, chunk_size, process_chunk, timeout)

    def _process_error_response(self, response):
        try:
            reason_type = response[1]
        except Exception as error:
            raise CorruptedResponse("Unable to extract reason type from response", error)

        if reason_type == Reason.BAD_REQUEST:
            raise BadRequestError
        elif reason_type == Reason.UNKNOWN_ERROR:
            try:
                message = response[2]
            except Exception as error:
                raise CorruptedResponse("Unable to extract message from error response", error)

            raise UnknownError(message)
        else:
            raise CorruptedResponse("Invalid reason type in error response")
