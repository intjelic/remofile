# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
import sys
from datetime import datetime
from pathlib import PurePosixPath, PosixPath
import click
from remofile.server import Server
from remofile.server import FILE_SIZE_LIMIT, MINIMUM_CHUNK_SIZE, MAXIMUM_CHUNK_SIZE
from remofile.client import Client
from remofile.exceptions import *
from remofile.token import generate_token
from remofile.daemon import Daemon

DEFAULT_TIMEOUT_VALUE = 3600

MISCONFIGURED_ENVIRONMENT_MESSAGE = """The environment must be \
configured with the following variables in order for Remofile to \
locate and connect to the server.

REMOFILE_HOSTNAME - Foobar.
REMOFILE_PORT     - The port to connect to. By default it uses 6768.
REMOFILE_TOKEN    - FOOBAR

Configure your environment and try again.
"""

TIMEOUT_ERROR_MESSAGE = """Timeout error; couldn't access the server \
within the expected time.

Check if the server is accessible or try to increase the timeout value \
for slow connection.
"""

GENERATED_TOKEN_MESSAGE = """The generated token is {0}, keep it \
secret because it acts as a password!

A token was generated because no token was specified in command-line \
parameters.
"""

INVALID_ROOT_DIRECTORY_MESSAGE = """The root directory isn't valid; \
either it doesn't exist or the server doesn't have the permissions to \
read it.

The root directory is the directory that is served across the network, \
therefore it must exist and be accessible.
"""

INCORRECT_VALUE_ERROR_MESSAGE = """One of the following values is \
incorrect.

* file size limit
* minimum chunk size
* maximum chunk size

Read the documentation to understand their possible value.
"""

def get_info_from_environment():
    hostname = os.environ.get("REMOFILE_HOSTNAME")
    port     = os.environ.get("REMOFILE_PORT", 6768)
    token    = os.environ.get("REMOFILE_TOKEN")

    if hostname == 'localhost':
        hostname = '127.0.0.1'

    return hostname, port, token

def create_client():
    # read environment variable for server information and print
    # misconfigured environment error if some variables are missing
    hostname, port, token = get_info_from_environment()

    if not hostname or not port or not token:
        print(MISCONFIGURED_ENVIRONMENT_MESSAGE)
        exit(1)

    return Client(hostname, port, token)

def adjust_timeout(timeout):
    # if not specified, adjust timeout to the default global timeout
    if not timeout:
        timeout = DEFAULT_TIMEOUT_VALUE

    return timeout

def display_generated_token(token):
    print(GENERATED_TOKEN_MESSAGE.format(token))

@click.group()
def cli():
    pass

@cli.command('list')
@click.argument('directory', default='/')
@click.option('--all', '-a', 'with_metadata', is_flag=True)
@click.option('--recursive', '-r', is_flag=True)
@click.option('--timeout', '-t', type=click.INT)
def list_files(directory, with_metadata, recursive, timeout):
    """ List files in the remote directory.

    This is a client-related command that lists files of a given
    directory located in the remote directory. This command is akin to
    the POSIX **ls** command found in Unix-like OSes.

    It takes only one **optional** parameter which is the remote
    directory to list files for, and must be an absolute path of an
    **existing** directory. By default, it lists the root directory.

    By default, it only displays file names and doesn't list the
    directory recursively. If the **-l** flag is set, it also lists the
    file metadata (file or directory indicator, file size and last
    modification time), and if the **-r** flag is set, the
    sub-directories are listed as well.

    Additionally, the **--timeout** flag allows you to adjust the number
    of milliseconds to wait before giving up on the server response.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    def display_directory_files(root, directory, with_metadata, recursive):
        try:
            files = client.list_files(os.path.join(root, directory), timeout)
        except ValueError:
            print("Unable to list files for '{0}' directory; it must be an absolute path.".format(directory))
            exit(1)
        except NotADirectoryError:
            print("Cannot access '{0}' directory; no such directory exists.".format(directory))
            exit(1)
        except TimeoutError:
            print(TIMEOUT_ERROR_MESSAGE)
            exit(1)

        subdirectories = []

        if not with_metadata:
            for name, (is_directory, _, _) in files.items():
                print(os.path.join(directory, name))

                if is_directory and recursive:
                    subdirectories.append(os.path.join(directory, name))
        else:
            # it requires double pass to compute columns width
            file_size_column_width = 0
            file_time_column_width = 0

            file_lines = []

            for name, (is_directory, file_size, file_time) in files.items():
                file_time = datetime.fromtimestamp(file_time)
                file_time_string = file_time.strftime('%Y-%m-%d %H:%M:%S')

                if not is_directory:
                    file_lines.append((os.path.join(directory, name), '[F]', str(file_size), file_time_string))
                else:
                    file_lines.append((os.path.join(directory, name), '[D]', str(file_size), file_time_string))

                file_size_column_width = max(file_size_column_width, len(str(file_size)))
                file_time_column_width = max(file_time_column_width, len(file_time_string))

                if is_directory and recursive:
                    subdirectories.append(os.path.join(directory, name))

            # add padding to column width
            file_size_column_width += 2

            for name, file_type, file_size, file_time in file_lines:
                print('{0} {1} {2} {3}'.format(file_type, file_size.ljust(file_size_column_width), file_time.ljust(file_time_column_width), name))

        for subdirectory in subdirectories:
            display_directory_files(root, subdirectory, with_metadata, recursive)

    display_directory_files(directory, '', with_metadata, recursive)

    del client # debug code, for some reason the socket wown't be disconnected

@cli.command('file')
@click.argument('name')
@click.argument('directory', default='/')
@click.option('--update', '-u', is_flag=True)
@click.option('--timeout', '-t', type=click.INT)
def create_file(name, directory, update, timeout):
    """ Create a file in the remote directory.

    This is a client-related command that creates an empty file in the
    a given directory located in the remote directory. This command is
    akin to the POSIX **touch** command found in Unix-like OSes.

    It takes the name of the file and an optional remote directory (in
    which to create the file) in parameters. The directory parameter
    must be an absolute path of an **existing** directory. By default,
    it creates the file in the root directory.

    If the file already exists in the given directory, the command fails
    unless the **--update** flag is set. Note that unlike the `touch`
    command, it doesn't update the file timestamp.

    Additionally, the **--timeout** flag allows you to adjust the number
    of milliseconds to wait before giving up on the server response.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    try:
        client.create_file(name, directory, timeout)
    except ValueError:
        print("Unable to create file in '{0}' directory; it must be an absolute path.".format(directory))
        exit(1)
    except InvalidFileName:
        print("Unable to create file with name '{0}'; it must be a valid file name.".format(name))
        exit(1)
    except NotADirectoryError:
        print("Cannot access '{0}' directory; no such directory exists.".format(directory))
        exit(1)
    except FileExistsError:
        if not update:
            print("Unable to create file with name '{0}'; it's conflicting with an existing file.".format(name))
            exit(1)
    except TimeoutError:
        print(TIMEOUT_ERROR_MESSAGE)
        exit(1)

    if directory == '/':
        print("File '{0}' successfuly created in root directory.".format(name))
    else:
        print("File '{0}' successfuly created in '{1}' directory.".format(name, directory))

@cli.command('folder')
@click.argument('name')
@click.argument('directory', default='/')
@click.option('--update', '-u', is_flag=True)
@click.option('--timeout', '-t', type=click.INT)
def make_directory(name, directory, update, timeout):
    """ Create a folder in the remote directory.

    This is a client-related command that creates an empty folder in the
    a given directory located in the remote directory. This command is
    akin to the POSIX **mkdir** command found in Unix-like OSes.

    It takes the name of the folder and an optional remote directory (in
    which to create the folder) in parameters. The directory parameter
    must be an absolute path of an **existing** directory. By default,
    it creates the folder in the root directory.

    If the folder already exists in the given directory, the command
    fails unless the **--update** flag is set. Note that it leaves the
    existing directory unchanged.

    Additionally, the **--timeout** flag allows you to adjust the number
    of milliseconds to wait before giving up on the server response.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    try:
        client.make_directory(name, directory, timeout)
    except ValueError:
        print("Unable to create folder in '{0}' directory; it must be an absolute path.".format(directory))
        exit(1)
    except InvalidFileName:
        print("Unable to create folder with name '{0}'; it must be a valid file name.".format(name))
        exit(1)
    except NotADirectoryError:
        print("Cannot access '{0}' directory; no such directory exists.".format(directory))
        exit(1)
    except FileExistsError:
        if not update:
            print("Unable to create folder with name '{0}'; it's conflicting with an existing file.".format(name))
            exit(1)
    except TimeoutError:
        print(TIMEOUT_ERROR_MESSAGE)
        exit(1)

    if directory == '/':
        print("Folder '{0}' successfuly created in root directory.".format(name))
    else:
        print("Folder '{0}' successfuly created in '{1}' directory.".format(name, directory))

#@click.option('--update', '-u')
##-u, --update copy only when the SOURCE file is newer than the destination file or when the destination file is missing
#@click.option('--resume')
#@click.option('--min-size', help="don't transfer any file smaller than SIZE")
#@click.option('--max-size', help="don't transfer any file larger than SIZE")
#--list-only             list the files instead of copying them
#--exclude=PATTERN       exclude files matching PATTERN
#--exclude-from=FILE     read exclude patterns from FILE
#--include=PATTERN       don't exclude files matching PATTERN
#--include-from=FILE     read include patterns from FILE
#@click.option('--out-format', help="output updates using the specified FORMAT")
#@click.option('--log-file', help="log what we're doing to the specified FILE")
#@click.option('--log-file-format', help="log updates using the specified FMT")
@cli.command('upload')
@click.argument('source', nargs=-1)
@click.argument('destination', nargs=1)
@click.option('--recursive', '-r', is_flag=True)
@click.option('--progress', '-p')
@click.option('--chunk-size', default=512, type=click.INT)
@click.option('--timeout', '-t', type=click.INT)
def upload_files(source, destination, recursive, progress, chunk_size, timeout):
    #min_size, max_size, out_format, log_file, log_file_format):
    """ Upload files to the remote directory.

    This is a client-related command that uploads files to the remote
    directory. The source must be files or directories on the local
    filesystem and the destination must be an **existing** directory in
    the remote directory. Unlike the source, the destination must be an
    absolute directory. If source refers to one or more directories, the
    recursiv flag must be set otherwise they'll be skipped.

    The progress flag allows to display the progression of the transfer
    which is useful for large files.

    Document chunk_size.
    Document timeout.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    # ensure we work with pure posix paths
    source = (PosixPath(path) for path in source)
    destination = PosixPath(destination)

    # foobar
    def process_chunk(chunk_data, remaining_bytes, file_size):
        # if progress flag was passed, show progress status
        #if progress:
        #name = source.name

        progress = (file_size - remaining_bytes) / file_size * 100

        #sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, name))
        sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, process_chunk.name))
        sys.stdout.flush()

        if remaining_bytes <= chunk_size:
            sys.stdout.write('\n')

        return True

    for path in source:
        if path.is_file():
            client.upload_file(path, destination, None, 512, process_chunk, timeout)
        elif path.is_dir():
            client.upload_directory(path, destination, None, 512, process_chunk, timeout)
        else:
            raise NotImplementedError

@cli.command('download')
@click.argument('source')
@click.argument('destination')
@click.option('--timeout', '-t', type=click.INT)
@click.option('--chunk-size', default=512, type=click.INT)
def download_files(source, destination, timeout, chunk_size):
    """ Download files from the remote directory.

    - source is either a file or a directory
    - if source is a directory, ensure --recursive is on, or abort the operation

    - destination must be a directory

    - timeout corresponds to time allowed between chunks

    Long description.
    """

    ## check if source is a file or a directory
    #source = PurePosixPath(source)
    #files = client.list_files(source.parent)
    #files = client.list_files(source.parent)
    #files = dict((name, (is_directory, size, last_accessed)) for name, is_directory, size, last_accessed in files)
    #is_directory = files[source.name] ==

    #is_directory = files[source.name] ==

    # if source is a directory, abort operation if no --recursive flag
    pass

    # check if destination is a directory, or abort the operation
    pass

    ## read environment variable for server information and print
    ## misconfigured environment error if some variables are missing
    #hostname, port, token = get_info_from_environment()

    #if not hostname or not port or not token:
        #print(MISCONFIGURED_ENVIRONMENT_MESSAGE)
        #exit(1)

    ## if not specified, adjust timeout to the default global timeout
    #if not timeout:
        #timeout = DEFAULT_TIMEOUT_VALUE

    #def process_chunk(chunk_data, remaining_bytes, file_size):
        ## do nothing for now...

        #return True

    #client = Client(hostname, port, token)
    #client.download_files(source, destination, chunk_size, process_chunk)

@cli.command('remove')
def remove_file():

    if not timeout:
        timeout = DEFAULT_TIMEOUT_VALUE

    pass

@cli.command('run')
@click.argument('directory')
@click.argument('port', default=6768)
@click.argument('token', required=False)
@click.option('--file-size-limit', default=FILE_SIZE_LIMIT,    type=click.INT)
@click.option('--min-chunk-size',  default=MINIMUM_CHUNK_SIZE, type=click.INT)
@click.option('--max-chunk-size',  default=MAXIMUM_CHUNK_SIZE, type=click.INT)
def run_server(directory, port, token, file_size_limit, min_chunk_size, max_chunk_size):
    """ Start a (non-daemonized) server.

    This is a server-related command that start a non-daemonized server
    (not detached from the shell). The directory parameter is the root
    directory which will be served and therefore must be an existing
    directory. The server listens on port 6768 by default but it can be
    changed with the port parameter. If the token is not specified, it's
    generated and printed out to the console before the server starts
    running.

    Additionally, the file size limit and the chunk size range can be
    altered. The file size limit and minimum chunk size must be both be
    greater than 0, and maximum chunk size must be greater or equal to
    minimum chunk size.
    """

    if not token:
        token = generate_token()
        display_generated_token(token)

    try:
        server = Server(directory, token, file_size_limit, min_chunk_size, max_chunk_size)
    except NotADirectoryError:
        print(INVALID_ROOT_DIRECTORY_MESSAGE)
        exit(1)
    except ValueError:
        print(INCORRECT_VALUE_ERROR_MESSAGE)
        exit(1)

    server.run('127.0.0.1', port)

@cli.command('start')
@click.argument('directory')
@click.argument('port', default=6768)
@click.argument('token', required=False)
@click.option('--pidfile', default=os.path.join(os.getcwd(), 'daemon.pid'))
@click.option('--file-size-limit', default=FILE_SIZE_LIMIT,    type=click.INT)
@click.option('--min-chunk-size',  default=MINIMUM_CHUNK_SIZE, type=click.INT)
@click.option('--max-chunk-size',  default=MAXIMUM_CHUNK_SIZE, type=click.INT)
def start_server(directory, port, token, pidfile, file_size_limit, min_chunk_size, max_chunk_size):
    """ Start a daemonized server.

    This is a server-related command that start a daemonized server
    (detached from the shell). Unlike the run command, it accepts the
    --pidfile flag which tells the pidfile location. By default, the
    pidfile is created in the current working directory and named
    'daemon.pid'.

    Refer to the run command for more information.
    """

    if not token:
        token = generate_token()
        display_generated_token(token)

    try:
        server = Server(directory, token, file_size_limit, min_chunk_size, max_chunk_size)
    except NotADirectoryError:
        print(INVALID_ROOT_DIRECTORY_MESSAGE)
        exit(1)
    except ValueError:
        print(INCORRECT_VALUE_ERROR_MESSAGE)
        exit(1)

    def loop():
        server.run('127.0.0.1', port)

    daemon = Daemon(loop, pidfile)
    daemon.start()

@cli.command('stop')
@click.option('--pidfile', default=os.path.join(os.getcwd(), 'daemon.pid'))
def stop_server(pidfile):
    """ Stop a daemonized server.

    This is a server-related command that stop a daemonized server from
    its pidfile. By default, it expects the pidfile in the current
    working directory with the name 'daemon.pid' but it can be altered
    with the --pidfile flag.
    """

    Daemon.stop(pidfile)

cli.add_command(list_files)
cli.add_command(create_file)
cli.add_command(make_directory)
cli.add_command(upload_files)
cli.add_command(download_files)
cli.add_command(remove_file)

cli.add_command(run_server)
cli.add_command(start_server)
cli.add_command(stop_server)


