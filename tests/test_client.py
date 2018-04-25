# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
import shutil
import threading
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
    operations.
    """

    def setUp(self):
        # create local working directory
        self.local_directory = TemporaryDirectory()
        self.local_directory_path = PosixPath(self.local_directory.name)

        # create remote working directory
        self.remote_directory = TemporaryDirectory()
        self.remote_directory_path = PosixPath(self.remote_directory.name)

        # start the server in an external thread
        self.server = Server(self.remote_directory_path, TOKEN)

        def server_loop(server):
            server.run(HOSTNAME, PORT)

        self.server_thread = threading.Thread(target=server_loop, args=(self.server,))
        self.server_thread.start()

        # change working direcory to local working directory
        self.last_working_directory = os.getcwd()
        os.chdir(self.local_directory_path)

    def tearDown(self):

        # restore current working directory
        os.chdir(self.last_working_directory)

        # terminate the server and wait until it terminates
        self.server.terminate()
        self.server_thread.join()

        # delete all testing contents in both local and remote working
        # directory
        self.local_directory.cleanup()
        self.remote_directory.cleanup()

    def _create_temporary_file(self, root, directory, name, size):
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

        It creates 'foo.bin' file and 'bar/' directory in the root
        directory and tests before and after if the correct dictionnary
        is returned.

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

        # test listing files of a non-existing directory
        with self.assertRaises(NotADirectoryError):
            client.list_files('/foo')

    def test_create_file(self):
        """ Test the create file method.

        It starts with creating a temporary working tree of files.

            /foo.bin
            /bar/qaz.txt

        Then, it attempts to create a file 'foo.bin' in 'bar' directory
        with invalid parameters to test each possible errors.

        It finishes with creating the file successfully and test if it
        has effectively been created.
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
            with self.assertRaises(InvalidFileName):
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

        with self.assertRaises(NotADirectoryError):
            client.create_file(name, invalid_directory)

        # test creating a file with valid parameters
        created_file = self.remote_directory_path / directory[1:] / name
        self.assertFalse(created_file.exists())

        client.create_file(name, directory)

        self.assertTrue(created_file.exists())
        self.assertTrue(created_file.is_file())

    def test_make_directories(self):
        """ Test the make directory method.

        It starts with creating a temporary working tree of files.

            /foo/
            /bar/qaz/

        Then, it attempts to create a directory 'foo/' in 'bar/'
        directory with invalid parameters to test each possible errors.

        It finishes with creating the directory successfully and test
        if it has effectively been created.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create remote working tree of files
        self.create_remote_directory('/', 'foo')
        self.create_remote_directory('/', 'bar')
        self.create_remote_directory('/', 'qaz')

        # prepare common variables
        name = 'foo'
        directory = '/bar'

        # test making a directory with an invalid name
        invalid_names = ['*baz', 'b"az', 'baz|']

        for invalid_name in invalid_names:
            with self.assertRaises(InvalidFileName):
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

        It starts with creating a local working directory and remote
        working directory as follow.

        Local working directory.

            foo.bin

        Remote working directory.

            bar/
            qaz/foo.bin

        Then it attempts to upload the local 'foo.bin' file to the
        remote 'bar/' directory. It does it by testing different foobar.

        It finishes with barfoo.
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

        # test uploading a file with a source file that doesn't exist
        # (todo: make 2 versions of it, one with source exists but is
        # not a file)
        with self.assertRaises(SourceNotFound):
            client.upload_file('foo.txt', destination, name, chunk_size, process_chunk)

        assert_file_not_uploaded(source, destination, 'foo.txt')

        # test uploading a file with destination being a relative path
        with self.assertRaises(ValueError):
            client.upload_file(source, 'bar', name, chunk_size, process_chunk)

        assert_file_not_uploaded(source, '/bar', name)

        # test uploading a file with a destination directory that
        # doesn't exist (todo: make 2 versions of it, one with
        # destination exist but is not a directory)
        with self.assertRaises(DestinationNotFound):
            client.upload_file(source, '/foo', name, chunk_size, process_chunk)

        assert_file_not_uploaded(source, '/foo', name)

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

        It starts with creating a local working directory and remote
        working directory as follow.

        Local working directory.

            foo/
                bar.bin
                qaz/xyz.img

        Remote working directory.

            foo/
            bar/

        Then, it attempts to upload the 'foo/' local directory to the
        'bar/' remote directory by trying different erroueonous versions.

        It finishes with foobar.

        To be written.
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

        # test uploading a directory with source is an relative path
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

        # test uploading a directory with a source directory that
        # doesn't exist (todo: make 2 versions of it, one with source
        # exists but is not a directory)
        with self.assertRaises(SourceNotFound):
            client.upload_directory('qaz', destination, name, chunk_size, process_chunk)

        # test uploading a directory with destination being a relative
        # path
        with self.assertRaises(ValueError):
            client.upload_directory(source, 'bar', name, chunk_size, process_chunk)

        # test uploading a directory with a destination directory that
        # doesn't exist (todo: make 2 versions of it, one with
        # destination exists but is not a directory)
        with self.assertRaises(DestinationNotFound):
            client.upload_directory(source, '/qaz', name, chunk_size, process_chunk)

        # test uploading a directory with an invalid chunk size
        with self.assertRaises(ValueError):
            client.upload_directory(source, destination, name, 0, process_chunk)

        # test uploading the directory again to ensure the previous
        # operations didn't correup the server state
        assert_directory_not_uploaded(source, destination, name)
        client.upload_directory(source, destination, name, chunk_size, process_chunk)

        assert_directory_uploaded(source, destination, name)
        delete_uploaded_directory(source, destination, name)

    def test_download_file(self):
        """ Test the download file method.

        It starts with creating a local working directory and remote
        working directory as follow.

        Local working directory.

            /bar/foo.bin
             qaz/

        Remote working directory.

            /bar/foo.bin

        Then it attempts to download the remote 'foo.bin' file to the
        local 'qaz/' directory. It does it by testing different foobar.

        It finishes with barfoo.
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

        # test downloading a file with a source file that doesn't exist
        # (todo: make 2 versions of it, one with source exists but is
        # not a file)
        with self.assertRaises(SourceNotFound):
            client.download_file('/foo.bin', destination, name, chunk_size, process_chunk)

        assert_file_not_downloaded('/foo.bin', destination, name)

        # test downloading a file with a destination directory that
        # doesn't exist (todo: make 2 versions of it, one with
        # destination exist but is not a directory)
        with self.assertRaises(DestinationNotFound):
            client.download_file(source, 'foo', name, chunk_size, process_chunk)

        assert_file_not_downloaded(source, 'foo', name)

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

        Local working directory.

            bar/
            qaz/foo

        Remote working directory.

            foo/
                bar.bin
                qaz/xyz.img

        Then, it attempts to download the 'foo/' remote directory to the
        'bar/' remote directory by trying different erroueonous versions.

        To be written.
        """

        # create client instance
        client = Client(HOSTNAME, PORT, TOKEN)

        # create local working tree of files
        self.create_local_directory('/', 'bar')
        self.create_local_directory('/', 'qaz')
        self.create_local_directory('/qaz', 'foo')

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

        # test downloading a directory with a source directory that doesn't exist
        # (todo: make 2 versions of it, one with source exists but is
        # not a file)
        with self.assertRaises(SourceNotFound):
            client.download_directory('/bar', destination, name, chunk_size, process_chunk)

        # test downloading a directory with a destination directory that
        # doesn't exist (todo: make 2 versions of it, one with
        # destination exist but is not a directory)
        with self.assertRaises(DestinationNotFound):
            client.download_directory(source, 'foo', name, chunk_size, process_chunk)

        assert_directory_not_downloaded(source, 'foo', name)

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

    #def test_remove_file(self):
        #""" Test the remove file method.

        #To be written.
        #"""

        ##pass
