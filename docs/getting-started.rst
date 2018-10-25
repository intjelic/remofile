The User Guide
==============
.. toctree::
   :hidden:

.. warning::

    The getting started document is still incomplete. Expect some
    serious update in the upcoming weeks.

This document aims to get you started with using Remofile. It covers the
installation, the key ideas you need to know, and shows how to use the main
features such as running a server, interacting with it from a shell and from
the code.

* Easy installation
* Run a testing server
* Shell interactions
* Remofile from Python codes
* Synchronizing directories
* Securing the connection
* Standalone server as a service
* Additional server options

For more exhaustive documentation, refer to the following documents; the
:doc:`commands list </commands-list>`, the :doc:`API reference </api-reference>`,
the :doc:`protocol specifications </protocol-specifications>`.

Easy installation
-----------------
Installing Remofile can't be easier. It doesn't have many dependencies
and it can be done in one command-line.

::

    pip install remofile

I suggest you create a virtual environment before typing this command.
This can easily be done like this.

::

    python3 -m virtualenv python-env
    source python-env/bin/activate

Installing with `pypi <https://pypi.org/>`_ in a virtual environment
provides flexibility as **Remofile** isn't installed system-wide. But
you can install with the underlying operating system package manager as
well. Packages for various Linux distributions do exist; check out the
following :doc:`document </packages>`.

Run a testing server
--------------------
Before deploying online, better do some **local** tests to familiarize
yourself with the tool. We'll start with running a local Remofile server
and interact with it.

Remofile doesn't know about users and passwords, instead you use a
token to authenticate.

::

    remofile generate-token

This generates a token which is a 16 letters long string. We'll be using
**qRkVWJcFRqi7rsNMbagaDd** for demonstration purpose. Copy paste it and
store it somewhere as it acts as a unique password.

Just like FTP, you want to jail and expose a directory to multiple
clients. It isn't too hard, the `run` command allows you to do just
that.

::

    mkdir my-directory/
    remofile run my-directory/ 6768 qRkVWJcFRqi7rsNMbagaDd

It takes the directory (that must be available across the network), the
port (on which to listen) and the previously generated token as
parameters.

This will run a Remofile server attached to the current console. Don't
expect this command to return... and don't interrupt it! Now, open
another console to continue.

.. note::

    The `start` and `stop` commands also starts a Remofile server, but
    instead it daemonizes the process and you work with a PID file instead.
    The command you use to start the server also impacts the way you
    run it as a service later.

    Also, if no token is given to the `run` command, one is
    automatically generated and printed out in the console before it
    starts.

Before we continue, we must understand an important aspect of Remofile;
its dumb nature. To have an uncomplicated tool to work with, Remofile
makes the assumption that all the files in the folder being served are
readable and writable by the user who started the process. It also makes
the assumption that the directory isn't modified (in any way) by
external mean while it's running. **But that should be common sense,
shouldn't it ?**

By not attempting to be smart, the overall interface and implementation
becomes simpler and easier to use. If these two assumptions aren't
respected, Remofile will still graciously fail with proper error
messages if something bad occurs during file operations.

Shell interactions
------------------
Our next step in experimenting Remofile will be with its command-line
interface. Even though it initially was designed for integration in
software (from code), it also has a powerful set of command-lines
allowing people to script interactions with the server.

Let's have a look at how to list files in the remote directory.
::

    remofile list /

In Remofile, there is no notion of "current working directory", and therefore,
the `/` refers to the root of the directory being served. This is also called
the **root directory**. Earlier we started the server to expose `my-directory/`,
so in this case, typing this command will list that directory.

.. important::

    Because there is no notion of **current working directory**, expect
    the entire programming and command-line interface to complain if a
    remote path isn't absolute.

The list command also comes with options. Type `remofile list --help` to know
more about them. For instance, it has options similar to the POSIX `ls` command
found in Unix-like OSes such as `-l` and `-r`. In one command, you can list the
entire content of the remote directory.
::

    remofile list / -l -r

There is also another important thing to understand. This is a **sessionless**
command. Instead of connecting to the server and prompting you to a different
interactive shell (supposedly with the connection maintained), it does connect
to the server, perform the file operation, then disconnect from the server. It
isn't efficient, but it provides a flexible mean for testing and scripting.

Upload and download files
-------------------------
Things get interesting when we actually get some files transferred to
and from the remote directory. The two main commands involved are
`upload` and `download`. They both support a dozen of options to
customize the behavior.

Both commands can transfer an **individual file**, an entire
**directory** (if the recursive flag is passed) or a **set of files**
specified by a shell glob patterns.

Have a look at the following.

::

    remofile upload single-file.txt a-directory/ **/some-text-files*.txt /
    remofile download single-file.txt a-directory/ .

We notice that the first arguments refer to the source files, and the
last argument refers to the destination. The destination must
imperatively be an existing directory on either the remote directory for
the upload command, or the local file-system for download command.

.. warning::

    Shell glob patterns would only work for the upload command as it's
    expanded by the underlying shell.

The destination directory actually is optional and is defaulted to
the root directory for the upload command, and the current working
directory for the download command. For instance, you can upload a file,
then download it back without thinking too much

    remofile upload ubuntu-16.04.3-desktop-amd64.iso
    remofile download ubuntu-16.04.3-desktop-amd64.iso

But these two commands merely are a front-end to the :py:func`upload_files`
and :py:func:`download_files` methods of the programming API. In fact,
all command-lines we saw so far have their actual corresponding
available available from Python.

Now we'll have a look at the programming interface because it's richer
than the command-line interface in terms of functionalities.

Remofile from Python code
-------------------------
Earlier, we saw how to start a Remofile server from the shell using the
`run` command. In fact, it can also be done in Python.

::

  from remofile import Server

  server = Server('my-directory', 'qRkVWJcFRqi7rsNMbagaDd')
  server.run(6768)

If the current working directory is the same as before, it will start
the Remofile server exactly like we did previously. The `run()` method
is blocking. To have it returning and thus, terminating the server, one
must call the `terminate()` from external thread.

.. note::

    By default, it listens to all IPs and this snipped of code is
    suitable for production code. Always refer to the API reference for
    exhaustive documentation.

But everything we did on the client side also trivially matches to a Python
programming interface.

::

  from remofile import Client

  client = Client('localhost', 6768, 'qRkVWJcFRqi7rsNMbagaDd')
  client.list_files('/')
  client.upload_file('foo', 'bar')
  client.download_file('bar', 'foo')

You quickly get it, it's exactly the same interface. In practice, you will
always use a timeout value and ensure that every file operations complete
successfully.

To be written here: words about the possible exceptions.

Synchronizing directories
-------------------------
Everything is already there to make decent use of Remofile. But synchronizing
directories would require additional logic on top of the primitive file
operations that the Client implements.

What if uploading a directory is interrupted and it's left partially uploaded.
An option would to delete the directory and re-do the upload from scratch.
However, this is costly, and using a synchronization approach would save tons of
bandwidth and time. Remofile spares you the hard work because that logic is
already there.

::

    from remofile import Client, synchronize_upload, synchronize_download

    client = Client('localhost', 6768)
    synchronize_upload('foo', 'bar')
    synchronize_download('bar', 'foo')

Foobar.

It also has a command version of .

::

    remofile sync local foo bar
    remofile sync remote bar foo

Foobar.

Securing your server
--------------------
Securing your server with private and public keys.

To be written.

Server as a deamon or service
-----------------------------

The last section of this guide will show you good practice when it comes to
installing a Remofile server on production server.

Additional server options
-------------------------

Talk about chunk size.
