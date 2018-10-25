# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import os
import time
import shutil
from multiprocessing import Process
from pathlib import PosixPath
from tempfile import TemporaryDirectory
import unittest
from click.testing import CliRunner
from remofile.server import Server
from remofile.cli import *
import remofile.token

HOSTNAME = '127.0.0.1'
PORT     = 6768
TOKEN    = remofile.token.generate_token()

class TestCLI(unittest.TestCase):
    """ Test the command-line interface.

    To be written.
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

            server.run(PORT)

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

    def test_list_command(self):
        """ Test the upload command.

        Remote working directory.

            foo/
                bar.bin
                qaz/xyz.img
            tox.iso

        Test invoking the following set of commands.

            rmf list
            rmf list /
            rmf list / -a
            rmf list / -r
            rmf list / -a -r
            rmf list /foo
            rmf list /foo -a
            rmf list /foo -r
            rmf list /foo -a -r

        Long description.
        """

        # create remote working tree of files
        self.create_remote_directory('/', 'foo')
        self.create_remote_file('/foo', 'bar.bin', 1052)
        self.create_remote_directory('/foo', 'qaz')
        self.create_remote_file('/foo/qaz', 'xyz.img', 312)
        self.create_remote_file('/', 'tox.iso', 860)

        # test with incorrectly configured environment
        runner = CliRunner()
        result = runner.invoke(list_files, [])
        self.assertIn('Configure your environment and try again.', result.output)
        self.assertEqual(result.exit_code, 1)

        time.sleep(0.05)

        # configure the environment
        os.environ["REMOFILE_HOSTNAME"] = 'localhost'
        os.environ["REMOFILE_PORT"]     = str(PORT)
        os.environ["REMOFILE_TOKEN"]    = TOKEN

        # test invoking command with minimal parameter
        runner = CliRunner()
        result = runner.invoke(list_files, [])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("foo",        result.output)
        self.assertIn("tox.iso",    result.output)
        self.assertNotIn("bar.bin", result.output)
        self.assertNotIn("qaz",     result.output)
        self.assertNotIn("xyz.img", result.output)

        default_exit_code = result.exit_code
        default_output    = result.output

        time.sleep(0.05)

        # test invoking command with default parameters
        runner = CliRunner()
        result = runner.invoke(list_files, ['/'])

        self.assertEqual(result.exit_code, default_exit_code)
        self.assertEqual(result.output, default_output)

        time.sleep(0.05)

        # test invoking command to list root with -a parameter
        runner = CliRunner()
        result = runner.invoke(list_files, ['/', '-a'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("[D]",        result.output)
        self.assertIn("foo",        result.output)
        self.assertIn("[F]",        result.output)
        self.assertIn("tox.iso",    result.output)
        self.assertNotIn("bar.bin", result.output)
        self.assertNotIn("qaz",     result.output)
        self.assertNotIn("xyz.img", result.output)

        time.sleep(0.05)

        # test invoking command to list root with -r parameter
        runner = CliRunner()
        result = runner.invoke(list_files, ['/', '-r'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("foo",             result.output)
        self.assertIn("tox.iso",         result.output)
        self.assertIn("foo/bar.bin",     result.output)
        self.assertIn("foo/qaz",         result.output)
        self.assertIn("foo/qaz/xyz.img", result.output)
        self.assertNotIn("[F]",          result.output)
        self.assertNotIn("[D]",          result.output)

        time.sleep(0.05)

        # test invoking command to list root with -a and -r parameters
        runner = CliRunner()
        result = runner.invoke(list_files, ['/', '-a', '-r'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("foo",             result.output)
        self.assertIn("tox.iso",         result.output)
        self.assertIn("foo/bar.bin",     result.output)
        self.assertIn("foo/qaz",         result.output)
        self.assertIn("foo/qaz/xyz.img", result.output)
        self.assertIn("[F]",             result.output)
        self.assertIn("[D]",             result.output)

        time.sleep(0.05)

        # test invoking command to list a subdirectory
        runner = CliRunner()
        result = runner.invoke(list_files, ['/foo'])

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("foo",         result.output)
        self.assertNotIn("tox.iso",     result.output)
        self.assertIn("bar.bin",        result.output)
        self.assertIn("qaz",            result.output)
        self.assertNotIn("qaz/xyz.img", result.output)
        self.assertNotIn("[F]",         result.output)
        self.assertNotIn("[D]",         result.output)

        time.sleep(0.05)

        # test invoking command to list a subdirectory with -a parameter
        runner = CliRunner()
        result = runner.invoke(list_files, ['/foo', '-a'])

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("foo",         result.output)
        self.assertNotIn("tox.iso",     result.output)
        self.assertIn("bar.bin",        result.output)
        self.assertIn("qaz",            result.output)
        self.assertNotIn("qaz/xyz.img", result.output)
        self.assertIn("[F]",            result.output)
        self.assertIn("[D]",            result.output)

        time.sleep(0.05)

        # test invoking command to list a subdirectory with -r parameter
        runner = CliRunner()
        result = runner.invoke(list_files, ['/foo', '-r'])

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("foo",      result.output)
        self.assertNotIn("tox.iso",  result.output)
        self.assertIn("bar.bin",     result.output)
        self.assertIn("qaz",         result.output)
        self.assertIn("qaz/xyz.img", result.output)
        self.assertNotIn("[F]",      result.output)
        self.assertNotIn("[D]",      result.output)

        time.sleep(0.05)

        # test invoking command to list a subdirectory with -a and -r parameters
        runner = CliRunner()
        result = runner.invoke(list_files, ['/foo', '-a', '-r'])

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("foo",      result.output)
        self.assertNotIn("tox.iso",  result.output)
        self.assertIn("bar.bin",     result.output)
        self.assertIn("qaz",         result.output)
        self.assertIn("qaz/xyz.img", result.output)
        self.assertIn("[F]",         result.output)
        self.assertIn("[D]",         result.output)

        time.sleep(0.05)

        # unset the environment
        del os.environ["REMOFILE_HOSTNAME"]
        del os.environ["REMOFILE_PORT"]
        del os.environ["REMOFILE_TOKEN"]

    def test_file_command(self):
        """ Test the upload command.

        Long description.
        """

        pass

    def test_folder_command(self):
        """ Test the upload command.

        Long description.
        """

        pass

    def test_upload_command(self):
        """ Test the upload command.

        Local working directory.

            foo/
                bar.bin
                qaz/xyz.img
            tox.iso

        To simplify tests, don't check binary content of uploaded files
        and subdirectories (this is covered by client tests).

        pass
        """

        # create loal working directory
        self.create_local_directory('/', 'foo')
        self.create_local_file('/foo', 'bar.bin', 1052)
        self.create_local_directory('/foo', 'qaz')
        self.create_local_file('/foo/qaz', 'xyz.img', 312)
        self.create_local_file('/', 'tox.iso', 860)

        tox_file_path = self.remote_directory_path / 'tox.iso'
        foo_directory_path = self.remote_directory_path / 'foo'

        # prepare common variables
        pass

        # test with incorrectly configured environment
        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', 'tox.iso'])
        self.assertIn('Configure your environment and try again.', result.output)
        self.assertEqual(result.exit_code, 1)

        time.sleep(0.05)

        # set the environment
        os.environ["REMOFILE_HOSTNAME"] = 'localhost'
        os.environ["REMOFILE_PORT"]     = str(PORT)
        os.environ["REMOFILE_TOKEN"]    = TOKEN

        # test upload one file
        self.assertFalse(tox_file_path.exists())

        runner = CliRunner()
        result = runner.invoke(upload_files, ['tox.iso', '/'])

        self.assertTrue(tox_file_path.is_file())
        self.assertEqual(result.exit_code, 0)
        print(result.output)

        os.remove(tox_file_path)

        time.sleep(0.05)

        # test upload one directory
        self.assertFalse(foo_directory_path.exists())

        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', '/'])
        self.assertEqual(result.exit_code, 0) # might change

        self.assertFalse(foo_directory_path.exists())

        time.sleep(0.05)

        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', '/', '-r'])
        self.assertEqual(result.exit_code, 0) # might change

        self.assertTrue(foo_directory_path.is_dir())

        shutil.rmtree(foo_directory_path)

        time.sleep(0.05)

        # test upload one file and one directory
        self.assertFalse(tox_file_path.exists())
        self.assertFalse(foo_directory_path.exists())

        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', 'tox.iso', '/'])
        self.assertEqual(result.exit_code, 0) # might change

        self.assertTrue(tox_file_path.is_file())
        self.assertFalse(foo_directory_path.exists())
        os.remove(tox_file_path)

        time.sleep(0.05)

        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', 'tox.iso', '/', '-r'])
        self.assertEqual(result.exit_code, 0) # might change

        self.assertTrue(tox_file_path.is_file())
        self.assertTrue(foo_directory_path.is_dir())

        os.remove(tox_file_path)
        shutil.rmtree(foo_directory_path)

        time.sleep(0.05)

        # test upload files with the progress flag
        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', 'tox.iso', '/', '-r'])
        self.assertEqual(result.exit_code, 0) # might change

        self.assertNotIn('bar.bin', result.output)
        self.assertNotIn('xyz.img', result.output)
        self.assertNotIn('tox.iso', result.output)
        self.assertEqual(result.output.count('100.00%'), 0)

        os.remove(tox_file_path)
        shutil.rmtree(foo_directory_path)

        time.sleep(0.05)

        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo', 'tox.iso', '/', '-r', '-p'])
        self.assertEqual(result.exit_code, 0) # might change

        self.assertIn('bar.bin', result.output)
        self.assertIn('xyz.img', result.output)
        self.assertIn('tox.iso', result.output)
        self.assertEqual(result.output.count('100.00%'), 3)

        os.remove(tox_file_path)
        shutil.rmtree(foo_directory_path)

        time.sleep(0.05)

        # test upload files with invalid source
        runner = CliRunner()
        result = runner.invoke(upload_files, ['foo.bin', '/'])
        self.assertEqual(result.exit_code, 1)
        self.assertIn('Unable to upload file', result.output)
        self.assertIn('no such file or directory exists', result.output)

        time.sleep(0.2)

        ## test upload files with relative destination path
        #runner = CliRunner()
        #result = runner.invoke(upload_files, ['foo', 'tox.iso', 'foo', '-r'])
        #self.assertEqual(result.exit_code, 1)
        #self.assertIn('Unable to upload files', result.output)
        #self.assertIn('destination must be an absolute path', result.output)

        #time.sleep(0.05)

        ## test upload files with unexisting destination
        #runner = CliRunner()
        #result = runner.invoke(upload_files, ['foo', 'tox.iso', '/foo', '-r'])
        #print(result.output)
        #self.assertEqual(result.exit_code, 1)
        #self.assertIn('Unable to upload files', result.output)
        #self.assertIn('no such directory exists', result.output)

        #time.sleep(0.2)

        ## test upload files with conflicting files
        #self.create_remote_file('/', 'tox.iso', 1204)

        #runner = CliRunner()
        #result = runner.invoke(upload_files, ['tox.iso', '/'])
        #self.assertEqual(result.exit_code, 1)
        #self.assertIn('Unable to upload file', result.output)
        #self.assertIn("it's conflicting with an existing file", result.output)

        #time.sleep(0.05)

        # test upload files with invalid names (shouldn't happen)
        pass

        # test min-size and max-size options
        pass


        # create remote working directory tree
        # /foo/
        #      bar/   -> existing directory
        #      qaz    -> existing file
        #
        # test uploading directory with no recursive flag enabled
        #  - bar
        #  - foo
        #
        # test uploading to incorrect destination directory
        #  - root directory (/)
        #  - directory whose parent is an unexsiting directory (/foo/qaz/bar)
        #  - directory whose parent is an existing directory but is an unexisting directory (/foo/qaz)
        #  - directory whose parent is an existing directory but is a existing file (/foo/qaz)
        #
        # test uploading a file that conflict with existing file (or
        # directory)
        #  - foo
        #  - bar
        #
        pass

    def test_download_command(self):
        """ Test the upload command.

        Long description.
        """

        pass

    def test_remove_command(self):
        """ Test the upload command.

        Long description.
        """

    def test_remove_command(self):
        """ Test the upload command.

        Long description.
        """

        pass

    def test_synchronize_local_command(self):
        """ Test the upload command.

        Long description.
        """

        pass

    def test_synchronize_remote_command(self):
        """ Test the upload command.

        Long description.
        """

        pass

    def test_generate_token_command(self):
        """ Test the generate-token command.

        It tests if the output is 8 characters long as it's expected to
        be a valid token.
        """

        env = self.get_testing_environment()

        runner = CliRunner(env=env)
        result = runner.invoke(generate_token, [])

        self.assertEqual(len(result.output), 23)
        self.assertEqual(result.exit_code, 0)

        time.sleep(1) # this is to give enough time to the server process to actually start

    def test_generate_keys_command(self):
        """ Test the generate-keys command.

        It tests if the output contains the "public key:" and "private
        key:" strings. Improvement of this test could check the length
        of the two keys as well as the set of characters.
        """

        env = self.get_testing_environment()

        runner = CliRunner(env=env)
        result = runner.invoke(generate_keys, [])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("public key:",  result.output)
        self.assertIn("private key:", result.output)

        time.sleep(1) # this is to give enough time to the server process to actually start
