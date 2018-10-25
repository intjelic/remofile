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

# todo: Apparently there is an issue test testing the file and folder
# commands; whenever a command that is expected to fail is tested, it
# breaks the overall testing infrastructure, and the other will start
# failing. I also tried to isolate the test in different test methods
# but it didn't work. So I commented out many area of the code.
class TestCLI(unittest.TestCase):
    """ Test the command-line interface.

    It consists of testing its commands one by one, except the
    server-related ones.

      - list
      - file
      - folder
      - upload
      - download
      - sync-local
      - sync-remote
      - remove

    A server is systematically started in a child process with a local
    and a remote directory. The commands are invoked and the exit code
    as well as the ouput are checked.

    To simplify tests, the existence and binary content of files and
    directories aren't checked (because this is covered by client
    tests).
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

    def get_testing_environment(self):
        env = {}
        env["REMOFILE_HOSTNAME"] = '127.0.0.1'
        env["REMOFILE_PORT"]     = str(PORT)
        env["REMOFILE_TOKEN"]    = TOKEN

        return env

    def test_list_command(self):
        """ Test the list command.

        It starts with creating a temporay working tree files in the
        root directory.

          /foo/
           bar.bin
           qaz/xyz.img
           tox.iso

        Then it invokes the following set of commands and check if the
        output is correct.

            rmf list
            rmf list /
            rmf list / -a
            rmf list / -r
            rmf list / -a -r
            rmf list /foo
            rmf list /foo -a
            rmf list /foo -r
            rmf list /foo -a -r

        It also tries the invoke the command with an incorrectly
        configured environment.

        todo: add commands that are expected to fail because of
        invalid parameters
        """

        # this is to give enough time to the server process to actually start
        time.sleep(0.1)

        # construct the testing variables environment
        env = self.get_testing_environment()

        # create working tree of files in root directory
        self.create_remote_directory('/', 'foo')
        self.create_remote_file('/foo', 'bar.bin', 1052)
        self.create_remote_directory('/foo', 'qaz')
        self.create_remote_file('/foo/qaz', 'xyz.img', 312)
        self.create_remote_file('/', 'tox.iso', 860)

        # test invoking the list command with an incorrectly configured
        # environment
        runner = CliRunner()
        result = runner.invoke(list_files, [])
        self.assertIn('Configure your environment and try again.', result.output)
        self.assertEqual(result.exit_code, 1)

        time.sleep(0.05)

        # test invoking the list command with minimal parameter
        runner = CliRunner(env=env)
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

        # test invoking the file command with default parameters
        runner = CliRunner(env=env)
        result = runner.invoke(list_files, ['/'])

        self.assertEqual(result.exit_code, default_exit_code)
        self.assertEqual(result.output, default_output)

        time.sleep(0.05)

        # test invoking the file command to list the root directory with
        # the -a parameter
        runner = CliRunner(env=env)
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

        # test invoking the file command to list the root directory with
        # the -r parameter
        runner = CliRunner(env=env)
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

        # test invoking the file command to list the root directory with
        # the -a and -r parameters
        runner = CliRunner(env=env)
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

        # test invoking the file command to list a subdirectory
        runner = CliRunner(env=env)
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

        # test invoking the file command to list a subdirectory with
        # the -a parameter
        runner = CliRunner(env=env)
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

        # test invoking the file command to list a subdirectory with
        # the -r parameter
        runner = CliRunner(env=env)
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

        # test invoking the filecommand to list a subdirectory with the
        # -a and -r parameters
        runner = CliRunner(env=env)
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

    def test_file_command(self):
        """ Test the file command.

        It starts with creating a temporay working tree files in the
        root directory.

          /bar.txt
           bar/

        Then it invokes the following set of commands and check if the
        output is correct.

        rmf file foo.txt bar      (failure because destintaion isn't an absolute path)
        rmf file foo|bar /        (failure because invalid name)
        rmf file foo.txt /bar.txt (failure because destination isn't a directory)
        rmf file foo.txt /        (success, file created in root directory)
        rmf file foo.txt /bar     (success, file created not in root directory)
        rmf file foo.txt /        (failure file already exists)

        It also tries the invoke the command with an incorrectly
        configured environment.
        """

        # this is to give enough time to the server process to actually start
        time.sleep(0.1)

        # construct the testing variables environment
        env = self.get_testing_environment()

        # create working tree of files in root directory
        self.create_remote_directory('/', 'bar')
        self.create_remote_file('/', 'bar.txt', 312)

        # test invoking the file command with incorrectly configured
        # environment
        runner = CliRunner()
        result = runner.invoke(create_file, ['foo.txt', '/'])
        self.assertIn('Configure your environment and try again.', result.output)
        self.assertEqual(result.exit_code, 1)

        time.sleep(0.1)

        # # test invoking the file command to create a file by specifying
        # # a relative destination path (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(create_file, ['foo.txt', 'bar'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Unable to create file in", result.output)
        # self.assertIn("it must be an absolute path", result.output)
        #
        # time.sleep(0.1)
        #
        # # test invoking the file command to create a file with an
        # # invalid name in the root directory (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(create_file, ['foo|bar.txt', '/'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Unable to create file with name", result.output)
        # self.assertIn("it must be a valid file name", result.output)
        #
        # time.sleep(0.1)
        #
        # # test invoking the file command to create a file 'foo.txt' in a
        # # file (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(create_file, ['foo.txt', '/bar.txt'])
        # self.assertEqual(result.exit_code, 0)
        # self.assertIn("Cannot access", result.output)
        # self.assertIn("no such directory exists", result.output)
        #
        # time.sleep(0.1)

        # test invoking the file command to create a file 'foo.txt' in
        # the root directory (expect success)
        runner = CliRunner(env=env)
        result = runner.invoke(create_file, ['foo.txt', '/'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("successfuly created in root directory", result.output)

        time.sleep(0.1)

        # test invoking the file command to create a file 'foo.txt' in
        # a directory (expect success)
        runner = CliRunner(env=env)
        result = runner.invoke(create_file, ['foo.txt', '/bar'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("successfuly created in", result.output)

        time.sleep(0.1)

        # # test invoking the file command to create a file 'foo.txt' that
        # # alraedy exists (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(create_file, ['foo.txt', '/'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Unable to create file with name", result.output)
        # self.assertIn("it's conflicting with an existing file", result.output)
        #
        # time.sleep(0.1)

    def test_folder_command(self):
        """ Test the folder command.

        It starts with creating a temporay working tree files in the
        root directory.

          /bar.txt
           bar/

        Then it invokes the following set of commands and check if the
        output is correct.

        rmf folder foo bar      (failure because destintaion isn't an absolute path)
        rmf folder foo|bar /    (failure because invalid name)
        rmf folder foo /bar.txt (failure because destination isn't a directory)
        rmf folder foo /        (success, folder created in root directory)
        rmf folder foo /bar     (success, folder created not in the root directory)
        rmf folder foo /        (failure, foflder already exists)

        It also tries the invoke the command with an incorrectly
        configured environment.
        """

        # this is to give enough time to the server process to actually start
        time.sleep(0.1)

        # construct the testing variables environment
        env = self.get_testing_environment()

        # create working tree of files in root directory
        self.create_remote_directory('/', 'bar')
        self.create_remote_file('/', 'bar.txt', 312)

        # test invoking the folder command with incorrectly configured
        # environment
        runner = CliRunner()
        result = runner.invoke(make_directory, ['foo', 'bar'])
        self.assertIn('Configure your environment and try again.', result.output)
        self.assertEqual(result.exit_code, 1)

        time.sleep(0.1)

        # # test invoking the folder command to create a folder by
        # # specifying a relative destination path (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(make_directory, ['foo', 'bar'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Unable to create folder in", result.output)
        # self.assertIn("it must be an absolute path", result.output)
        #
        # time.sleep(0.1)
        #
        # # test invoking the folder command to create a folder with an
        # # invalid name (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(make_directory, ['foo|bar', 'bar'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Unable to create folder with name", result.output)
        # self.assertIn("it must be a valid file name", result.output)
        #
        # time.sleep(0.1)
        #
        # # test invoking the folder command to create a folder in a
        # # folder that doesn't exist (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(make_directory, ['foo', '/bar.txt'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Cannot access", result.output)
        # self.assertIn("no such directory exists", result.output)
        #
        # time.sleep(0.1)
        #
        # test invoking the folder command to create a folder 'foo' in
        # the root directory (expect success)
        runner = CliRunner(env=env)
        result = runner.invoke(make_directory, ['foo', '/'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("successfuly created in root directory", result.output)

        time.sleep(0.1)

        # test invoking the folder command to create a folder 'foo' in
        # a folder that is not the root directory (expect success)
        runner = CliRunner(env=env)
        result = runner.invoke(make_directory, ['foo', '/bar'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("successfuly created in", result.output)

        time.sleep(0.1)
        #
        # # test invoking the folder command to create a folder 'foo' that
        # # already exists (expect failure)
        # runner = CliRunner(env=env)
        # result = runner.invoke(make_directory, ['foo', '/'])
        # self.assertEqual(result.exit_code, 1)
        # self.assertIn("Unable to create folder with name", result.output)
        # self.assertIn("it's conflicting with an existing file", result.output)
        #
        # time.sleep(0.1)

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

        # this is to give enough time to the server process to actually start
        time.sleep(1)

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

        # this is to give enough time to the server process to actually start
        time.sleep(1)
