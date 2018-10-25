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
from remofile.keys import generate_keys
from remofile.daemon import Daemon

DEFAULT_TIMEOUT_VALUE = 3600

MISCONFIGURED_ENVIRONMENT_MESSAGE = """The environment must be \
configured with the following variables in order for Remofile to \
locate and connect to the server.

REMOFILE_HOSTNAME - The ip address to use (can be 'localhost' or a domain name)
REMOFILE_PORT     - The port to use (optional, use 6768 by default)
REMOFILE_TOKEN    - The token to use during the authentication process

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

INCORRECT_CONFIG_VALUE_MESSAGE = """One of the following values is \
incorrect.

* file size limit
* minimum chunk size
* maximum chunk size

Read the documentation to understand their possible value.
"""

LIST_ALL_FLAG_DESCRIPTION           = "Display additional file information."
LIST_RECURSIVE_FLAG_DESCRIPTION     = "List directories and their contents recursively."
FILE_UPDATE_FLAG_DESCRIPTION        = "Ignore (and don't fail) if files already exist."
FOLDER_UPDATE_FLAG_DESCRIPTION      = "Ignore (and don't fail) if directories already exist."
UPLOAD_RECURSIVE_FLAG_DESCRIPTION   = "Upload directories and their content recursively."
DOWNLOAD_RECURSIVE_FLAG_DESCRIPTION = "Download directories and their content recursively."
PROGRESS_FLAG_DESCRIPTION           = "Display a progress indicator."
TIMEOUT_FLAG_DESCRIPTION            = "Adjust the timeout value in milliseconds."
FILE_SIZE_LIMIT_FLAG_DESCRIPTION    = "Foobar"
MIN_CHUNK_SIZE_FLAG_DESCRIPTION     = "Foobar"
MAX_CHUNK_SIZE_FLAG_DESCRIPTION     = "Foobar"
PIDFILE_FLAG_DESCRIPTION            = "Foobar"

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
@click.option('--all',       '-a', 'with_metadata', is_flag=True, help=LIST_ALL_FLAG_DESCRIPTION)
@click.option('--recursive', '-r', is_flag=True,                  help=LIST_RECURSIVE_FLAG_DESCRIPTION)
@click.option('--timeout',   '-t', type=click.INT,                help=TIMEOUT_FLAG_DESCRIPTION)
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
@click.option('--update',  '-u', is_flag=True,   help=FILE_UPDATE_FLAG_DESCRIPTION)
@click.option('--timeout', '-t', type=click.INT, help=TIMEOUT_FLAG_DESCRIPTION)
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
    except FileNameError:
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
@click.option('--update',  '-u', is_flag=True,   help=FOLDER_UPDATE_FLAG_DESCRIPTION)
@click.option('--timeout', '-t', type=click.INT, help=TIMEOUT_FLAG_DESCRIPTION)
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
    except FileNameError:
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
#@click.option('--chunk-size', default=512, type=click.INT)
@cli.command('upload')
@click.argument('source', nargs=-1)
@click.argument('destination', nargs=1)
@click.option('--recursive', '-r', is_flag=True,   help=UPLOAD_RECURSIVE_FLAG_DESCRIPTION)
@click.option('--progress',  '-p', is_flag=True,   help=PROGRESS_FLAG_DESCRIPTION)
@click.option('--timeout',   '-t', type=click.INT, help=TIMEOUT_FLAG_DESCRIPTION)
def upload_files(source, destination, recursive, progress, timeout):
    """ Upload files to the remote directory.

    This is a client-related command that uploads files to the remote
    directory. The source must be files or directories located on the
    local filesystem and the destination must be an **existing**
    directory located in the remote directory. Unlike the source, the
    destination must be an absolute path.

    If source refers to one or more directories, the recursive flag must
    be set otherwise they'll be skipped. The progress flag allows to
    display the progression of the transfer which is useful for large
    files.

    Examples. ::

        rmf upload -r -p src/my-file.txt src/my-directory/ /dst

    Additionally, the **--timeout** flag allows you to adjust the number
    of milliseconds to wait before giving up on the server response.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    # ensure we work with pure posix paths
    source = (PosixPath(path) for path in source)
    destination = PosixPath(destination)

    def display_progress(chunk_data, remaining_bytes, file_size, file_name):

        chunk_size = 512
        progress = (file_size - (remaining_bytes - len(chunk_data))) / file_size * 100

        sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, file_name))
        sys.stdout.flush()

        if remaining_bytes <= chunk_size:
            sys.stdout.write('\n')

        return True

    def upload_file(path):
        try:
            if progress:
                client.upload_file(path, destination, None, 512, display_progress, None)
            else:
                client.upload_file(path, destination, timeout=timeout)
        except ValueError:
            print("Unable to upload files to '{0}'; destination must be an absolute path.".format(destination))
            exit(1)
        except SourceNotFound:
            print("Unable to upload file '{0}'; no such file exists.".format(path))
            exit(1)
        except DestinationNotFound:
            print("Unable to upload files to '{0}'; no such directory exists.".format(destination))
            exit(1)
        except FileExistsError:
            print("Unable to upload file '{0}'; it's conflicting with an existing file.".format(path))
            exit(1)
        except FileNameError:
            raise NotImplementedError
        except TimeoutError:
            print(TIMEOUT_ERROR_MESSAGE)
            exit(1)

    def upload_directory(path):
        try:
            if progress:
                client.upload_directory(path, destination, None, 512, display_progress, None)
            else:
                client.upload_directory(path, destination, timeout=timeout)
        except ValueError:
            print("Unable to upload files to '{0}'; destination must be an absolute path.".format(destination))
            exit(1)
        except SourceNotFound:
            print("Unable to upload folder '{0}'; no such directory exists.".format(path))
            exit(1)
        except DestinationNotFound:
            print("Unable to upload files to '{0}'; no such directory exists.".format(destination))
            exit(1)
        except FileExistsError:
            print("Unable to upload folder '{0}'; it's conflicting with an existing file.".format(path))
            exit(1)
        except FileNameError:
            raise NotImplementedError
        except TimeoutError:
            print(TIMEOUT_ERROR_MESSAGE)
            exit(1)

    for path in source:
        if not path.exists():
            print("Unable to upload file '{0}'; no such file or directory exists.".format(path))
            exit(1)

        if path.is_file():
            upload_file(path)
        elif path.is_dir():
            if recursive:
                upload_directory(path)
            else:
                print("Skip uploading folder '{0}'; the recursive flag must be set.".format(path))
        else:
            raise NotImplementedError("Uploading symbolic links isn't supported yet.")

    del client # debug code, for some reason the socket wown't be disconnected

@cli.command('download')
@click.argument('source', nargs=-1)
@click.argument('destination', nargs=1)
@click.option('--recursive', '-r', is_flag=True,   help=DOWNLOAD_RECURSIVE_FLAG_DESCRIPTION)
@click.option('--progress',  '-p', is_flag=True,   help=PROGRESS_FLAG_DESCRIPTION)
@click.option('--timeout',   '-t', type=click.INT, help=TIMEOUT_FLAG_DESCRIPTION)
def download_files(source, destination, recursive, progress, timeout):
    """ Download files from the remote directory.

    This is a client-related command that downloads files from the
    remote directory. The source must be files or directories located on
    the remote directory and the destination must be an **existing**
    directory located on the local filesystem. Unlike the destination,
    the source must be absolute paths.

    If source refers to one or more directories, the recursive flag must
    be set otherwise they'll be skipped. The progress flag allows to
    display the progression of the transfer which is useful for large
    files.

    Examples. ::

        rmf download -r -p /src/my-file.txt /src/my-directory/ dst/

    Additionally, the **--timeout** flag allows you to adjust the number
    of milliseconds to wait before giving up on the server response.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    # ensure we work with pure posix paths
    source = (PurePosixPath(path) for path in source)
    destination = PosixPath(destination)

    def display_progress(chunk_data, remaining_bytes, file_size, file_name):

        chunk_size = 512
        progress = (file_size - (remaining_bytes - len(chunk_data))) / file_size * 100

        sys.stdout.write("\r{0:0.2f}% | {1}".format(progress, file_name))
        sys.stdout.flush()

        if remaining_bytes <= chunk_size:
            sys.stdout.write('\n')

        return True

    def download_file(path):
        try:
            if progress:
                client.download_file(path, destination, None, 512, display_progress, None)
            else:
                client.download_file(path, destination, timeout=timeout)
        except Exception as error:
            print(error)
            exit(1)

        #except ValueError:
            #print("Unable to upload files to '{0}'; destination must be an absolute path.".format(destination))
            #exit(1)
        #except SourceNotFound:
            #print("Unable to upload file '{0}'; no such file exists.".format(path))
            #exit(1)
        #except DestinationNotFound:
            #print("Unable to upload files to '{0}'; no such directory exists.".format(destination))
            #exit(1)
        #except FileExistsError:
            #print("Unable to upload file '{0}'; it's conflicting with an existing file.".format(path))
            #exit(1)
        #except FileNameError:
            #raise NotImplementedError
        #except TimeoutError:
            #print(TIMEOUT_ERROR_MESSAGE)
            #exit(1)

    def download_directory(path):
        try:
            if progress:
                client.download_directory(path, destination, None, 512, display_progress, None)
            else:
                client.download_directory(path, destination, timeout=timeout)
        except Exception as error:
            print(error)
            exit(1)
        #except ValueError:
            #print("Unable to upload files to '{0}'; destination must be an absolute path.".format(destination))
            #exit(1)
        #except SourceNotFound:
            #print("Unable to upload folder '{0}'; no such directory exists.".format(path))
            #exit(1)
        #except DestinationNotFound:
            #print("Unable to upload files to '{0}'; no such directory exists.".format(destination))
            #exit(1)
        #except FileExistsError:
            #print("Unable to upload folder '{0}'; it's conflicting with an existing file.".format(path))
            #exit(1)
        #except FileNameError:
            #raise NotImplementedError
        #except TimeoutError:
            #print(TIMEOUT_ERROR_MESSAGE)
            #exit(1)

    for path in source:

        is_directory = True

        if path != '/':
            files = client.list_files(path.parent)

            if path.name not in files:
                print("Unable to download file '{0}'; no such file or directory exists.".format(path))
                exit(1)

            is_directory = files[path.name][0]

        if not is_directory:
            download_file(path)
        else:
            if recursive:
                download_directory(path)
            else:
                print("Skip downloading folder '{0}'; the recursive flag must be set.".format(path))

    del client # debug code, for some reason the socket won't be disconnected

@cli.command('remove')
@click.argument('name')
@click.argument('directory', default='/')
@click.option('--timeout', '-t', type=click.INT, help=TIMEOUT_FLAG_DESCRIPTION)
def remove_files(name, directory, timeout):
    """ Remove files in the remote directory.

    This is a client-related command that removes a file or a folder
    located in the remote directory. This command is akin to the POSIX
    **rm** command found in Unix-like OSes.

    Rest of the description here.
    """

    client = create_client()
    timeout = adjust_timeout(timeout)

    pass

@cli.command('run')
@click.argument('directory')
@click.argument('port', default=6768)
@click.argument('token', required=False)
@click.option('--file-size-limit', default=FILE_SIZE_LIMIT,    type=click.INT, help=FILE_SIZE_LIMIT_FLAG_DESCRIPTION)
@click.option('--min-chunk-size',  default=MINIMUM_CHUNK_SIZE, type=click.INT, help=MIN_CHUNK_SIZE_FLAG_DESCRIPTION)
@click.option('--max-chunk-size',  default=MAXIMUM_CHUNK_SIZE, type=click.INT, help=MAX_CHUNK_SIZE_FLAG_DESCRIPTION)
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
        server = Server(directory, token,
            file_size_limit=file_size_limit,
            chunk_size_range=(min_chunk_size, max_chunk_size))
    except NotADirectoryError:
        print(INVALID_ROOT_DIRECTORY_MESSAGE)
        exit(1)
    except ValueError:
        print(INCORRECT_CONFIG_VALUE_MESSAGE)
        exit(1)

    server.run(port)

@cli.command('start')
@click.argument('directory')
@click.argument('port', default=6768)
@click.argument('token', required=False)
@click.option('--pidfile', default=os.path.join(os.getcwd(), 'daemon.pid'),    help=PIDFILE_FLAG_DESCRIPTION)
@click.option('--file-size-limit', default=FILE_SIZE_LIMIT,    type=click.INT, help=FILE_SIZE_LIMIT_FLAG_DESCRIPTION)
@click.option('--min-chunk-size',  default=MINIMUM_CHUNK_SIZE, type=click.INT, help=MIN_CHUNK_SIZE_FLAG_DESCRIPTION)
@click.option('--max-chunk-size',  default=MAXIMUM_CHUNK_SIZE, type=click.INT, help=MAX_CHUNK_SIZE_FLAG_DESCRIPTION)
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
        print(INCORRECT_CONFIG_VALUE_MESSAGE)
        exit(1)

    def loop():
        server.run(port)

    daemon = Daemon(loop, pidfile)
    daemon.start()

@cli.command('stop')
@click.option('--pidfile', default=os.path.join(os.getcwd(), 'daemon.pid'), help=PIDFILE_FLAG_DESCRIPTION)
def stop_server(pidfile):
    """ Stop a daemonized server.

    This is a server-related command that stop a daemonized server from
    its pidfile. By default, it expects the pidfile in the current
    working directory with the name 'daemon.pid' but it can be altered
    with the --pidfile flag.
    """

    Daemon.stop(pidfile)

@cli.command('generate-token')
def generate_token():
    """ Generate a token.

    This is an utility command that generates a valid token needed to
    configure both the client and the server.

    Note that by default, the server will generate a token if none was
    explicitly set.
    """

    from remofile.token import generate_token
    print(generate_token())

@cli.command('generate-keys')
def generate_keys():
    """ Generate a pair of keys.

    This is an utility command that generates a valid pair of keys to
    encrypt communication with clients.

    The first key is a public key that must be shared across clients
    connecting to the Remofile server and the second key is the private
    key that must be kept secret. Both :py:class:`Client` and
    :py:class:`Server` instances must be configured with their
    respective keys.
    """

    from remofile.keys import generate_keys
    public_key, private_key = generate_keys()

    print("public key: {0}".format(str(public_key, 'utf-8')))
    print("private key: {0}".format(str(private_key, 'utf-8')))

cli.add_command(list_files)
cli.add_command(create_file)
cli.add_command(make_directory)
cli.add_command(upload_files)
cli.add_command(download_files)
cli.add_command(remove_files)

cli.add_command(run_server)
cli.add_command(start_server)
cli.add_command(stop_server)

cli.add_command(generate_token)
cli.add_command(generate_keys)
