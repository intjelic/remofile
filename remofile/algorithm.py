# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, April 2018


# enum Conflict
#   - REPLACE
#   - RENAME
#   - SKIP
#   - ABORT

def upload_files(client, source, destination, relative_directory):
    #exclude_files=[],
    #process_file=None,
    #process_directory=None,
    #process_conflict=False,
    #chunk_size=CHUNK_SIZE,
    #process_chunk=None,
    #timeout=None):
    """ Upload files to the remote directory.

    This method uploads one file, an entire directory or a set of
    files (specified by glob patterns) to a given directory in the
    remote directory.

    The source parameter refers to the local file(s) to be
    transfered to the remote directory and must to be a path-like
    object of a relative directory that can contain glob patterns.
    Source files are related to the directory specified by the relative_directory parameter which
    itself must be a path-like object of an **existing** absolute
    directory. By default, the relative directory is the current
    working directory. If the source is a directory or refers to
    sub-directories, the recursive parameter must be set.

    The destination parameter refers to the remote directory in
    which the file(s) must be transfered to. It must be a path-like
    object aof an **existing** absolute directory.

    The exclude_files parameter is a sequence of path-like objects
    of relative path (that may or may not contain glob patterns)
    that refers to files to be excluded from the transfer.

    The timeout parameter corresponds to time allowed to send each
    chunk.

    :param source: Foobar.
    :param destination: Foobar.
    :param chunk_size: Foobar.
    :type chunk_size: int
    :param process_chunk: Foobar.
    :param timeout: How many milliseconds to wait before giving up
    :type timeout: int
    """

    import os
    import fnmatch
    from pathlib import PurePosixPath

    # todo: check source isn't empty
    # test: check if . and .. works

    # ensure we work with pure posix paths
    source = PurePosixPath(source)
    relative_directory = PurePosixPath(relative_directory)

    destination = PurePosixPath(destination)

    exclude_files = [PurePosixPath(exclude_file) for exclude_file in exclude_files]

    # raise "source must be a relative path" error if source is an
    # absolute path
    if source.is_absolute():
        raise ValueError("Source must be a relative path")

    # raise "relative directory must be an absolute path" error if
    # relative_directory is a relative path
    if not relative_directory.is_absolute():
        raise ValueError("Relative directory must be an absolute path")

    # check relative directory is an existing directory (and ensure
    # it doens't contain glob patterns ?)
    if not relative_directory.exists() or not relative_directory.is_dir():
        raise AssertionError # to be replaced with actual exception

    # check if destination directory is an existing directory (and
    # ensure it doens't contain glob patterns ?)
    if not destination.exists() or not destination.is_dir():
        raise AssertionError # to be replaced with actual exception

    # build list of files to upload
    files_list = []

    def has_glob_pattern(path):
        return '*' in str(path) or '?' in str(path)

    if has_glob_pattern(source):

        # build list of files according to the glob patterns
        pass
    else:
        source = relative_directory / source
        # check if the file (or directory) exist
        if source.exist():
            if source.is_file():
                pass
            elif source.is_dir():
                pass
            else:
                raise AssertionError

    for foo in os.listdir(os.getcwd()):
        print(foo)
        print(fnmatch.fnmatch(foo, str(source)))

    #if is_glob_pattern(source):
        #pass
    #else:
        #pass

def download_files(client, source, destination, relative_directory):
    #chunk_size=CHUNK_SIZE, process_chunk=None, timeout=None):
    """ Download files from the remote directory.

    This method downloads one file, an entire directory or a set of
    files (specified by shell glob pattern) to a given directory in
    in the local filesystem. Additional parameters are there to
    refine the process.

    The source parameter refers to the remote file(s) to be
    transfered to the local filesystem and is expected to be a
    path-like object, unless it's a shell glob pattern in which case
    a string is expected. The path must be relative and is by
    default relative to the root directory. It can be
    altered with the relative_directory parameter which itself must
    be path-like object refering to an absolute directory.

    The destination parameter refers to the remote directory in
    which the file(s) must be transfered to. It must be a path-like
    object and must be absolute.

    Long description.

    :param source: Foobar.
    :param destination: Foobar.
    :param chunk_size: Foobar.
    :type chunk_size: int
    :param process_chunk: Foobar.
    :param timeout: How many milliseconds to wait before giving up
    :type timeout: int
    """

    pass
    ## compute destination directory and file name from source
    #directory = os.path.dirname(source)
    #name      = os.path.basename(source)
    #assert name != ''

    ## adjust destination path to be an absolute path
    #if not os.path.isabs(destination):
        #destination = os.path.join(os.getcwd(), destination)

    ## todo: check if path actually exist

    #print(directory)
    #print(name)
    #print(destination)

    #request = make_download_file_request(name, directory, chunk_size)
    #self.socket.send_pyobj(request)

    #response = self.socket.recv_pyobj()
    #print(response)

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

def synchronize_upload(client, source, destination):
    """ Synchronize remote files with a local directory.

    Long description.
    """

    raise NotImplementedError

def synchronize_download(client, source, destination):
    """ Synchronize local files with a remote directory.

    Long description.
    """

    raise NotImplementedError
