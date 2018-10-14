# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
import shutil
from multiprocessing import Process
from pathlib import PurePosixPath, PosixPath
from tempfile import TemporaryDirectory
import unittest
from remofile.server import Server
from remofile.client import Client
from remofile.token import generate_token
from remofile.protocol import *
from remofile.exceptions import *

HOSTNAME = '127.0.0.1'
PORT     = 6768
TOKEN    = generate_token()

class TestClient(unittest.TestCase):
    """ Test the client class.

    It consists of testing its methods that implement all native file
    operations one by one.

      - test_list_files()
      - test_create_file()
      - test_make_directory()
      - test_upload_file()
      - test_upload_directory()
      - test_download_file()
      - test_download_directory()
      - test_remove_directory()

    A server is systematically started in a child process with a local
    and a remote directory. The client does file operation and checks if
    the local and remote directories are in the expected state.
    """

    def setUp(self):
        # create local working directory
        self.local_directory = TemporaryDirectory()
        self.local_directory_path = PosixPath(self.local_directory.name)

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

        # change working direcory to local working directory
        self.last_working_directory = os.getcwd()
        os.chdir(self.local_directory_path)

    def tearDown(self):

        # restore current working directory
        os.chdir(self.last_working_directory)

        # terminate the server (send SIGTERM) and wait until child process
        # terminates
        self.server_process.terminate()
        self.server_process.join()

        # delete all testing contents in both local and remote working
        # directory
        self.local_directory.cleanup()
        self.remote_directory.cleanup()

    def _create_temporary_file(self, root, directory, name, size):
        """ Create a temporary file in the 'remote' directory.

        This function creates a temporary file with a given name in a
        given directory located in the temporary working 'remote'
        directory. It's filled with a given amount of random data.

        It returns a posix path of the created file and the generated
        data.
        """

        assert os.path.isabs(directory) == True
        directory = directory[1:]

        file_data = os.urandom(size)

        temporary_file_path = root / directory / name
        temporary_file = temporary_file_path.open('wb')
        temporary_file.write(file_data)
        temporary_file.close()

        return temporary_file_path, file_data

    def _create_temporary_directory(self, root, directory, name):
        """ Create a temporary directory in the 'remote' directory.

        This function creates a temporary directory with a given name
        in a given directory located in the temporary workinng 'remote'
        directory.

        It returns a posix path of the created directory.
        """

        assert os.path.isabs(directory) == True
        directory = directory[1:]

        temporary_directory_path = root / directory / name
        temporary_directory_path.mkdir(exist_ok=False)

        return temporary_directory_path

    def create_local_file(self, directory, name, size):
        return self._create_temporary_file(self.local_directory_path, directory, name, size)

    def create_local_directory(self, directory, name):
        return self._create_temporary_directory(self.local_directory_path, directory, name)

    def create_remote_file(self, directory, name, size):
        return self._create_temporary_file(self.remote_directory_path, directory, name, size)

    def create_remote_directory(self, directory, name):
        return self._create_temporary_directory(self.remote_directory_path, directory, name)

    def test_list_files(self):
        """ Test the list files method.

        It creates 'foo.bin' file and 'bar/' directory in the remote
        directory and then it tests, before and after, if the correct
        dictionnary is returned.

        It ends with testing listing files with a relative path (which
        is not permitted) and listing files of a non-existing directory.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # test listing files of the empty root directory
        files = client.list_files('/')
        self.assertDictEqual(files, {})

        # test listing files of root directory  after creating 'foo.bin'
        # and 'bar/' in it
        file_path, _   = self.create_remote_file('/', 'foo.bin', 1052)
        directory_path = self.create_remote_directory('/', 'bar')

        expected_files = {
            'foo.bin' : (False, 1052, file_path.stat().st_atime),
            'bar'     : (True,     0, directory_path.stat().st_atime)
        }

        files = client.list_files('/')
        self.assertDictEqual(files, expected_files)

        # test listing files with a relative directory
        with self.assertRaises(ValueError):
            client.list_files('bar')

        # test listing files of a directory that doesn't exist
        with self.assertRaises(FileNotFoundError):
            client.list_files('/foo')

        # test listing files of a directory that actually is a file
        with self.assertRaises(NotADirectoryError):
            client.list_files('/foo.bin')

    def test_create_file(self):
        """ Test the create file method.

        It starts with creating a temporary working tree of files in the
        remote directory as follow.

          /foo.bin
           bar/qaz.txt

        Then, it attempts to create a file 'foo.bin' in the 'bar'
        directory using the create_file() method. It tries it with
        different variants of invalid set of parameters to check if
        errors are correctly triggered.

        Incorrect variants of invalid parameters.

          - test creating a file with invalid names
          - test creating a file with a conflicting name
          - test creating a file with a relative directory
          - test creating a file with a non-existing directory

        It finishes with creating the file successfully (using a set of
        valid parameters) and test if the file has effectively been
        created.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create remote working tree of files
        self.create_remote_file('/', 'foo.bin', 1052)
        self.create_remote_directory('/', 'bar')
        self.create_remote_file('/bar', 'qaz.txt', 431)

        # prepare common variables
        name = 'foo.bin'
        directory = '/bar'

        # test creating a file with an invalid name
        invalid_names = ['*baz', 'b"az', 'baz|']

        for invalid_name in invalid_names:
            with self.assertRaises(FileNameError):
                client.create_file(invalid_name, directory)

        # test creating a file with a conflicting name
        invalid_directory = '/'

        with self.assertRaises(FileExistsError):
            client.create_file(name, invalid_directory)

        # test creating a file with a relative directory
        invalid_directory = 'bar'

        with self.assertRaises(ValueError):
            client.create_file(name, invalid_directory)

        # test creating a file with a non-existing directory
        invalid_directory = '/foo'

        with self.assertRaises(FileNotFoundError):
            client.create_file(name, invalid_directory)

        # test creating a file with a directory that is not an actual
        # directory
        invalid_directory = '/foo.bin'

        with self.assertRaises(NotADirectoryError):
            client.create_file(name, invalid_directory)

        # test creating a file with valid parameters
        created_file = self.remote_directory_path / directory[1:] / name
        self.assertFalse(created_file.exists())

        client.create_file(name, directory)

        self.assertTrue(created_file.exists())
        self.assertTrue(created_file.is_file())

    def test_make_directory(self):
        """ Test the make directory method.

        It starts with creating a temporary working tree of files in the
        remote directory as follow.

          /foo/
           bar/qaz/
           foo.bin

        Then, it attempts to create a directory 'foo/' in the 'bar/'
        directory using the make_directory() method. It tries it with
        different variants of invalid set of parameters to check if
        errors are correctly triggerd.

        Incorrect variants of invalid parameters.

          - test making a directory with invalid names
          - test making a directory with a conflicting name
          - test making a directory with a relative directory
          - test making a directory with a non-existing directory

        It finishes with creating the directory successfully (using a
        set of valid parameters) and test if the directory has
        effectively been created.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create remote working tree of files
        self.create_remote_directory('/', 'foo')
        self.create_remote_directory('/', 'bar')
        self.create_remote_directory('/', 'qaz')
        self.create_remote_file('/', 'foo.bin', 1052)

        # prepare common variables
        name = 'foo'
        directory = '/bar'

        # test making a directory with an invalid name
        invalid_names = ['*baz', 'b"az', 'baz|']

        for invalid_name in invalid_names:
            with self.assertRaises(FileNameError):
                client.make_directory(invalid_name, directory)

        # test making a directory with a conflicting name
        invalid_directory = '/'

        with self.assertRaises(FileExistsError):
            client.make_directory(name, invalid_directory)

        # test making a directory with a relative directory
        invalid_directory = 'bar'

        with self.assertRaises(ValueError):
            client.make_directory(name, invalid_directory)

        # test making a directory with a non-existing directory
        invalid_directory = '/foo/bar'

        with self.assertRaises(FileNotFoundError):
            client.make_directory(name, invalid_directory)

        # test making a directory with a directory that isn't an actual
        # directory
        invalid_directory = '/foo.bin'

        with self.assertRaises(NotADirectoryError):
            client.make_directory(name, invalid_directory)

        # test making a directory with valid parameters
        created_directory = self.remote_directory_path / directory[1:] / name
        self.assertFalse(created_directory.exists())

        client.make_directory(name, directory)

        self.assertTrue(created_directory.exists())
        self.assertTrue(created_directory.is_dir())

    def test_upload_file(self):
        """ Test the upload file method.

        It starts with creating temporary working trees of files in both
        the local and remote directories, as follow.

          $(local_dir)/foo.bin
                       bar/

          $(remote_dir)/bar/
                        qaz/foo.bin

        Then it attempts to upload the local 'foo.bin' file to the
        remote 'bar/' directory using the upload_file() method. It tries
        it with different set of parameters, either valid or invalid,
        and systematically check if the operation was successfully or
        not. If this is successful, it checks that the binary content is
        correct, and if it's a failure, it checks if the exceptions are
        triggered correctly.

        Different set of valid and invalid parameters.

          - test uploading a file with source is a relative path
          - test uploading a file with source is an absolute path
          - test uploading a file with changing its name
          - test uploading a file with source being a file that doesn't exist
          - test uploading a file with source being a directory (and not a file)
          - test uploading a file with destination being a relative path
          - test uploading a file with destination being a directory that doesn't exist
          - test uploading a file with destination being a file (and not a directory)
          - test uploading a file with a name that conflicts with an existing file in the destination directory
          - test uploading a file with an invalid chunk size
          - test uploading a file with a custom process chunk callback
          - test uploading a file with a custom process chunk callback that interupts the upload
          - test uploading a file with a custom process chunk callback that raises an exception
          - test uploading a file with chunk size greater than the file size being uploaded

        It finishes with uploading the file successfully (using a set of
        valid parameters) and test if the file has effectively been
        uploaded.

        Note that checking the file size limit is done in server-related
        tests.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create local working tree of files
        _, file_data = self.create_local_file('/', 'foo.bin', 1052)

        # create remote working tree of files
        self.create_remote_directory('/', 'bar')
        self.create_remote_directory('/', 'qaz')
        self.create_remote_file('/qaz', 'foo.bin', 1052)

        # prepare common variables
        source = 'foo.bin'
        destination = '/bar'
        name = None
        chunk_size = 512
        process_chunk = None

        # prepare assert routines
        def assert_file_not_uploaded(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            uploaded_file_path = self.remote_directory_path / destination[1:] / name
            self.assertFalse(uploaded_file_path.exists())

        def assert_file_uploaded(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            uploaded_file_path = self.remote_directory_path / destination[1:] / name
            self.assertTrue(uploaded_file_path.is_file())

            uploaded_file = uploaded_file_path.open('rb')
            self.assertEqual(uploaded_file.read(), file_data)
            uploaded_file.close()

        def delete_uploaded_file(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            uploaded_file_path = self.remote_directory_path / destination[1:] / name
            os.remove(uploaded_file_path)

        # test uploading a file with source is a relative path
        assert_file_not_uploaded(source, destination, name)

        client.upload_file(source, destination, name, chunk_size, process_chunk)

        assert_file_uploaded(source, destination, name)
        delete_uploaded_file(source, destination, name)

        # test uploading a file with source is an absolute path
        assert_file_not_uploaded(source, destination, name)

        client.upload_file(self.local_directory_path / source, destination, name, chunk_size, process_chunk)

        assert_file_uploaded(source, destination, name)
        delete_uploaded_file(source, destination, name)

        # test uploading a file with changing its name
        assert_file_not_uploaded(source, destination, 'bar.bin')

        client.upload_file(source, destination, 'bar.bin', chunk_size, process_chunk)

        assert_file_uploaded(source, destination, 'bar.bin')
        delete_uploaded_file(source, destination, 'bar.bin')

        # test uploading a file with source being a file that doesn't
        # exist
        with self.assertRaises(SourceNotFound):
            client.upload_file('foo.txt', destination, name, chunk_size, process_chunk)

        # test uploading a file with source being a directory (and not a
        # file)
        with self.assertRaises(SourceNotFound):
            client.upload_file('bar', destination, name, chunk_size, process_chunk)

        # test uploading a file with destination being a relative path
        with self.assertRaises(ValueError):
            client.upload_file(source, 'bar', name, chunk_size, process_chunk)

        # test uploading a file with destination being a directory that
        # doesn't exist
        with self.assertRaises(DestinationNotFound):
            client.upload_file(source, '/foo', name, chunk_size, process_chunk)

        # test uploading a file with destination being a file (and not a
        # directory)
        with self.assertRaises(DestinationNotFound):
            client.upload_file(source, '/qaz/foo.bin', name, chunk_size, process_chunk)

        # test uploading a file with a name that conflicts with an
        # existing file in the destination directory
        with self.assertRaises(FileExistsError):
            client.upload_file(source, '/qaz', name, chunk_size, process_chunk)

        # test uploading a file with an invalid chunk size
        with self.assertRaises(ValueError):
            client.upload_file(source, destination, name, 0, process_chunk)

        assert_file_not_uploaded(source, destination, name)

        # test uploading a file with a custom process chunk callback
        expected_chunk_data = (file_data[:512], file_data[512:1024], file_data[1024:])
        expected_remaining_bytes = (1052, 1052-512, 1052-512-512)

        def custom_process_chunk(chunk_data, remaining_bytes, file_size, file_name):
            self.assertEqual(chunk_data, expected_chunk_data[custom_process_chunk.counter])
            self.assertEqual(remaining_bytes, expected_remaining_bytes[custom_process_chunk.counter])
            self.assertEqual(file_size, 1052)

            custom_process_chunk.counter += 1

            return True

        custom_process_chunk.counter = 0

        assert_file_not_uploaded(source, destination, name)

        client.upload_file(source, destination, name, 512, custom_process_chunk)
        self.assertEqual(custom_process_chunk.counter, 3)

        assert_file_uploaded(source, destination, name)
        delete_uploaded_file(source, destination, name)

        # test uploading a file with a custom process chunk callback
        # that interupts the upload
        def custom_process_chunk(chunk_data, remaining_bytes, file_size, file_name):
            custom_process_chunk.counter += 1

            if custom_process_chunk.counter == 1:
                return False

            return True

        custom_process_chunk.counter = 0

        client.upload_file(source, destination, name, chunk_size, custom_process_chunk)
        assert_file_not_uploaded(source, destination, name)

        # test uploading a file with a custom process chunk callback
        # that raises an exception
        class CustomException(Exception):
            pass

        def custom_process_chunk(chunk_data, remaining_bytes, file_size, file_name):
            raise CustomException()

        with self.assertRaises(CustomException):
                client.upload_file(source, destination, name, chunk_size, custom_process_chunk)

        assert_file_not_uploaded(source, destination, name)

        # test uploading a file with chunk size greater than the file
        # size being uploaded
        assert_file_not_uploaded(source, destination, name)

        client.upload_file(source, destination, name, 4096, process_chunk)

        assert_file_uploaded(source, destination, name)
        delete_uploaded_file(source, destination, name)

        # test uploading a file again to ensure the previous operations
        # didn't corrupt the server state
        assert_file_not_uploaded(source, destination, name)

        client.upload_file(source, destination, name, chunk_size, process_chunk)

        assert_file_uploaded(source, destination, name)
        delete_uploaded_file(source, destination, name)

    def test_upload_directory(self):
        """ Test the upload directory method.

        It starts with creating temporary working trees of files in both
        the local and remote directories, as follow.

          $(local_dir)/foo/bar.bin
                           qaz/xyz.img

          $(remote_dir)/foo/
                        bar/
                        qaz.bin

        Then it attempts to upload the local 'foo/' directory to the
        remote 'bar/' directory using the upload_directory() method. It
        tries it with different set of parameters, either valid or
        invalid, and systematically check if the operation was
        successfully or not. If this is successful, it checks that the
        binary content is correct, and if it's a failure, it checks if
        the exceptions are triggered correctly.

        Different set of valid and invalid parameters.

          - test uploading a directory with source is a relative path
          - test uploading a directory with source is an absolute path
          - test uploading a directory with changing its name
          - test uploading a directory with source being a file that doesn't exist
          - test uploading a directory with source being a directory (and not a file)
          - test uploading a directory with destination being a relative path
          - test uploading a directory with destination being a directory that doesn't exist
          - test uploading a directory with destination being a file (and not a directory)
          - test uploading a directory with a name that conflicts with an existing file in the destination directory
          - test uploading a directory with an invalid chunk size

        It finishes with uploading the directory successfully (using a
        set of valid parameters) and test if the directory has
        effectively been uploaded.

        Note that unlike the upload file test, it doesn't check the
        chunk processing callback function. And also, the file size
        limit is checked in the server-related tests.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create local working directory
        self.create_local_directory('/', 'foo')
        _, bar_file_data = self.create_local_file('/foo', 'bar.bin', 1052)
        self.create_local_directory('/foo', 'qaz')
        _, xyz_file_data = self.create_local_file('/foo/qaz', 'xyz.img', 321)

        # create remote working directory
        self.create_remote_directory('/', 'foo')
        self.create_remote_directory('/', 'bar')
        self.create_remote_file('/', 'qaz.bin', 42)

        # prepare common variables
        source = 'foo'
        destination = '/bar'
        name = None
        chunk_size = 512
        process_chunk = None

        # prepare assert routines
        def assert_directory_not_uploaded(source, destination, name=None):
            if not name:
                name = PosixPath(source).name

            uploaded_directory_path = self.remote_directory_path / destination[1:] / name
            self.assertFalse(uploaded_directory_path.exists())

        def assert_directory_uploaded(source, destination, name=None):
            if not name:
                name = PosixPath(source).name

            # assert foo/
            foo_directory_path = self.remote_directory_path / destination[1:] / name
            self.assertTrue(foo_directory_path.is_dir())

            # assert foo/bar.bin
            bar_file_path = self.remote_directory_path / destination[1:] / name / 'bar.bin'
            self.assertTrue(bar_file_path.is_file())
            self.assertEqual(bar_file_path.open('rb').read(), bar_file_data)

            # assert foo/qaz
            qaz_directory_path = self.remote_directory_path / destination[1:] / name / 'qaz'
            self.assertTrue(qaz_directory_path.is_dir())

            # assert foo/qaz/xyz.img
            xyz_file_path = self.remote_directory_path / destination[1:] / name / 'qaz/xyz.img'
            self.assertTrue(xyz_file_path.is_file())
            self.assertEqual(xyz_file_path.open('rb').read(), xyz_file_data)

        def delete_uploaded_directory(source, destination, name=None):
            if not name:
                name = PosixPath(source).name

            uploaded_directory_path = self.remote_directory_path / destination[1:] / name
            shutil.rmtree(uploaded_directory_path)

        # test uploading a directory with source is a relative path
        assert_directory_not_uploaded(source, destination, name)
        client.upload_directory(self.local_directory_path / source, destination, name, chunk_size, process_chunk)
        assert_directory_uploaded(source, destination, name)

        delete_uploaded_directory(source, destination, name)

        # test uploading a directory with source is an absolute path
        assert_directory_not_uploaded(source, destination, name)
        client.upload_directory(source, destination, name, chunk_size, process_chunk)
        assert_directory_uploaded(source, destination, name)

        delete_uploaded_directory(source, destination, name)

        # test uploading a directory with changing its name
        assert_directory_not_uploaded(source, destination, 'qux')
        client.upload_directory(source, destination, 'qux', chunk_size, process_chunk)
        assert_directory_uploaded(source, destination, 'qux')

        delete_uploaded_directory(source, destination, 'qux')

        # test uploading a directory with source being a directory that
        # doesn't exist
        with self.assertRaises(SourceNotFound):
            client.upload_directory('qaz', destination, name, chunk_size, process_chunk)

        assert_directory_not_uploaded(source, destination, 'qux')

        # test uploading a directory with source being a file (and not a
        # directory)
        with self.assertRaises(SourceNotFound):
            client.upload_directory('foo/bar.bin', destination, name, chunk_size, process_chunk)

        # test uploading a directory with destination being a relative
        # path
        with self.assertRaises(ValueError):
            client.upload_directory(source, 'bar', name, chunk_size, process_chunk)

        # test uploading a directory with destination being a directory
        # that doesn't exist
        with self.assertRaises(DestinationNotFound):
            client.upload_directory(source, '/qaz', name, chunk_size, process_chunk)

        # test uploading a directory with destination being a file (and
        # not a directory)
        with self.assertRaises(DestinationNotFound):
            client.upload_directory(source, '/qaz.bin', name, chunk_size, process_chunk)

        # test uploading a directory with a name that conflicts with an
        # existing file in the destination directory
        with self.assertRaises(FileExistsError):
            client.upload_directory(source, '/', name, chunk_size, process_chunk)

        # test uploading a directory with an invalid chunk size
        with self.assertRaises(ValueError):
            client.upload_directory(source, destination, name, 0, process_chunk)

        # test uploading the directory again to ensure the previous
        # operations didn't corrupt the server state
        assert_directory_not_uploaded(source, destination, name)
        client.upload_directory(source, destination, name, chunk_size, process_chunk)

        assert_directory_uploaded(source, destination, name)
        delete_uploaded_directory(source, destination, name)

    def test_download_file(self):
        """ Test the download file method.

        It starts with creating temporary working trees of files in both
        the local and remote directories, as follow.

          $(local_dir)/bar/foo.bin
                       qaz/

          $(remote_dir)/bar/foo.bin

        Then it attempts to download the remote 'foo.bin' file to the
        local 'qaz/' directory using the download_file() method. It
        tries it with different variants of invalid set of parameters to
        check if errors are corectly triggered.

        Incorrect variants of invalid parameters.

          - test downloading a file with destination is a relative path
          - test downloading a file with destination is an absolute path
          - test downloading a file with changing its name
          - test downloading a file with source being a relative path
          - test downloading a file with source being a file that doens't exist
          - test downloading a file with source being a directory (and not a file)
          - test downloading a file with destination being a directory that doesn't exist
          - test downloading a file with destination being a file (and not a directory)
          - test downloading a file with a name that conflicts with an existing file in the destination directory
          - [TODO] test downloading a file with an invalid chunk size
          - [TODO] test downloading a file with a custom process chunk callback
          - [TODO] test downloading a file with a custom process chunk callback that interupts the upload
          - [TODO] test downloading a file with chunk size greater than the file size being uploaded

        It finishes with downloading the file successfully (using a set
        of valid parameters) and test if the file has effectively been
        downloaded.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create local working tree of files
        self.create_local_directory('/', 'bar')
        self.create_local_directory('/', 'qaz')
        self.create_local_file('/bar', 'foo.bin', 1052)

        # create remote working tree of files
        self.create_remote_directory('/', 'bar')
        _, file_data = self.create_remote_file('/bar', 'foo.bin', 1052)

        # prepare common variables
        source = '/bar/foo.bin'
        destination = 'qaz'
        name = None
        chunk_size = 512
        process_chunk = None

        # prepare assert routines
        def assert_file_not_downloaded(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            downloaded_file_path = self.local_directory_path / destination / name
            self.assertFalse(downloaded_file_path.exists())

        def assert_file_downloaded(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            downloaded_file_path = self.local_directory_path / destination / name
            self.assertTrue(downloaded_file_path.is_file())

            downloaded_file = downloaded_file_path.open('rb')
            self.assertEqual(downloaded_file.read(), file_data)
            downloaded_file.close()

        def delete_downloaded_file(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            downloaded_file_path = self.local_directory_path / destination / name
            os.remove(downloaded_file_path)

        # test downloading a file with destination is a relative path
        assert_file_not_downloaded(source, destination, name)

        client.download_file(source, destination, name, chunk_size, process_chunk)

        assert_file_downloaded(source, destination, name)
        delete_downloaded_file(source, destination, name)

        # test downloading a file with destination is an absolute path
        assert_file_not_downloaded(source, destination, name)

        client.download_file(source, self.local_directory_path / destination, name, chunk_size, process_chunk)

        assert_file_downloaded(source, destination, name)
        delete_downloaded_file(source, destination, name)

        # test downloading a file with changing its name
        assert_file_not_downloaded(source, destination, 'bar.bin')

        client.download_file(source, destination, 'bar.bin', chunk_size, process_chunk)

        assert_file_downloaded(source, destination, 'bar.bin')
        delete_downloaded_file(source, destination, 'bar.bin')

        # test downloading a file with source being a relative path
        with self.assertRaises(ValueError):
            client.download_file('bar/foo.bin', destination, name, chunk_size, process_chunk)

        assert_file_not_downloaded('bar/foo.bin', destination, name)

        # test downloading a file with source being a file that doens't
        # exist
        with self.assertRaises(SourceNotFound):
            client.download_file('/foo.bin', destination, name, chunk_size, process_chunk)

        # test downloading a file with source being a directory (and not
        # a file)
        with self.assertRaises(SourceNotFound):
            client.download_file('/bar', destination, name, chunk_size, process_chunk)

        # test downloading a file with destination being a directory
        # that doesn't exist
        with self.assertRaises(DestinationNotFound):
            client.download_file(source, 'foo', name, chunk_size, process_chunk)

        # test downloading a file with destination being a file (and not
        # a directory)
        with self.assertRaises(DestinationNotFound):
            client.download_file(source, 'bar/foo.bin', name, chunk_size, process_chunk)

        # test downloading a file with a name that conflicts with an
        # existing file in the destination directory
        with self.assertRaises(FileExistsError):
            client.download_file(source, 'bar', name, chunk_size, process_chunk)

        # test downloading a file with an invalid chunk size
        with self.assertRaises(ValueError):
            client.download_file(source, destination, name, 0, process_chunk)

        assert_file_not_downloaded(source, destination, name)

        # test downloading a file with a custom process chunk callback
        pass

        # test downloading a file with a custom process chunk callback
        # that interupts the upload
        pass

        # test downloading a file with chunk size greater than the file
        # size being uploaded
        pass

        # test downloading a file again to ensure the previous operations
        # didn't corrupt the server state
        pass

    def test_download_directory(self):
        """ Test the download directory method.

        It starts with creating temporary working trees of files in both
        the local and remote directories, as follow.

          $(local_dir)/bar/
                       qaz/foo
                       foo.bin

          $(remote_dir)/foo/bar.bin
                            qaz/xyz.img

        Then it attempts to download the remote 'foo/' directory to the
        local 'bar/' directory using the download_directory() method. It
        tries it with different variants of invalid set of parameters to
        check if errors are corectly triggered.

        Incorrect variants of invalid parameters.

          - test downloading a directory with destination is a relative path
          - test downloading a directory with destination is an absolute path
          - test downloading a directory with changing its name
          - test downloading a directory with source being a relative path
          - test downloading a directory with a source directory that doesn't exist (todo: make 2 versions of it, one with source exists but is not a file)
          - [CHECK-ME] is anything missing here ?
          - test downloading a directory with a destination directory that doesn't exist (todo: make 2 versions of it, one with  destination exist but is not a directory)
          - test downloading a directory with a name that conflicts with an existing file in the destination directory
          - test downloading a directory with an invalid chunk size
          - test downloading a directory again to ensure the previous operations didn't corrupt the server state

        It finishes with downloading the directory successfully (using
        a set of valid parameters) and test if the directory has
        effectively been downloaded.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create local working tree of files
        self.create_local_directory('/', 'bar')
        self.create_local_directory('/', 'qaz')
        self.create_local_directory('/qaz', 'foo')
        self.create_local_file('/', 'foo.bin', 42)

        # create remote working tree of files
        self.create_remote_directory('/', 'foo')
        _, bar_file_data = self.create_remote_file('/foo', 'bar.bin', 1052)
        self.create_remote_directory('/foo', 'qaz')
        _, xyz_file_data = self.create_remote_file('/foo/qaz', 'xyz.img', 312)

        # prepare assert routines
        def assert_directory_not_downloaded(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            downloaded_directory_path = self.local_directory_path / destination / name
            self.assertFalse(downloaded_directory_path.exists())

        def assert_directory_downloaded(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            # assert foo/
            foo_directory_path = self.local_directory_path / destination / name
            self.assertTrue(foo_directory_path.is_dir())

            # assert foo/bar.bin
            bar_file_path = self.local_directory_path / destination / name / 'bar.bin'
            self.assertTrue(bar_file_path.is_file())
            self.assertEqual(bar_file_path.open('rb').read(), bar_file_data)

            # assert foo/qaz
            qaz_directory_path = self.local_directory_path / destination / name / 'qaz'
            self.assertTrue(qaz_directory_path.is_dir())

            # assert foo/qaz/xyz.img
            xyz_file_path = self.local_directory_path / destination / name / 'qaz/xyz.img'
            self.assertTrue(xyz_file_path.is_file())
            self.assertEqual(xyz_file_path.open('rb').read(), xyz_file_data)

        def delete_downloaded_directory(source, destination, name=None):
            if not name:
                name = PurePosixPath(source).name

            downloaded_directory_path = self.local_directory_path / destination / name
            shutil.rmtree(downloaded_directory_path)

        # prepare common variables
        source = '/foo'
        destination = 'bar'
        name = None
        chunk_size = 512
        process_chunk = None

        # test downloading a directory with destination is a relative path
        assert_directory_not_downloaded(source, destination, name)

        client.download_directory(source, destination, name, chunk_size, process_chunk)

        assert_directory_downloaded(source, destination, name)
        delete_downloaded_directory(source, destination, name)

        # test downloading a directory with destination is an absolute path
        assert_directory_not_downloaded(source, destination, name)

        client.download_directory(source, self.local_directory_path / destination, name, chunk_size, process_chunk)

        assert_directory_downloaded(source, destination, name)
        delete_downloaded_directory(source, destination, name)

        # test downloading a directory with changing its name
        assert_directory_not_downloaded(source, destination, 'bar')

        client.download_directory(source, destination, 'bar', chunk_size, process_chunk)

        assert_directory_downloaded(source, destination, 'bar')
        delete_downloaded_directory(source, destination, 'bar')

        # test downloading a directory with source being a relative path
        with self.assertRaises(ValueError):
            client.download_directory('foo', destination, name, chunk_size, process_chunk)

        assert_directory_not_downloaded(source, destination, name)

        # test downloading a directory with source being a directory
        # that doesn't exist
        with self.assertRaises(SourceNotFound):
            client.download_directory('/bar', destination, name, chunk_size, process_chunk)
        #
        # # test downloading a directory with source being a file (and not
        # # a directory)
        # with self.assertRaises(SourceNotFound):
        #     client.download_directory('/foo/bar.bin', destination, name, chunk_size, process_chunk)

        # test downloading a directory with destination being a
        # directory that doesn't exist
        with self.assertRaises(DestinationNotFound):
            client.download_directory(source, 'foo', name, chunk_size, process_chunk)

        # test downloading a directory with destination being a file
        # (and not a directory)
        with self.assertRaises(DestinationNotFound):
            client.download_directory(source, 'foo.bin', name, chunk_size, process_chunk)

        # test downloading a directory with a name that conflicts with an
        # existing file in the destination directory
        with self.assertRaises(FileExistsError):
            client.download_directory(source, 'qaz', name, chunk_size, process_chunk)

        # test downloading a directory with an invalid chunk size
        with self.assertRaises(ValueError):
            client.download_directory(source, destination, name, 0, process_chunk)

        assert_directory_not_downloaded(source, destination, name)

        # test downloading a directory again to ensure the previous operations
        # didn't corrupt the server state
        assert_directory_not_downloaded(source, destination, name)

        client.download_directory(source, destination, name, chunk_size, process_chunk)

        assert_directory_downloaded(source, destination, name)
        delete_downloaded_directory(source, destination, name)

    def test_remove_file(self):
        """ Test the remove file method.

        To be written.
        """

        pass
