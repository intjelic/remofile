The User Guide
==============
.. toctree::
   :hidden:

.. warning::

    The user guide is still fairly incomplete. Expect some serious
    update in the upcoming weeks.

The user guide gets you started with using Remofile. It covers the
installation and the main features. For more exhaustive documentation,
refer to the respective documents (the :doc:`commands list
</commands-list>`, the :doc:`API reference </api-reference>`, the
:doc:`protocol specifications </protocol-specifications>`)

* Easy installation
* Run a testing server
* Shell interactions
* Synchronizing directories
* A look at the programming interface
* Securing the connection
* Standalone server as a service

Easy installation
-----------------
Installing Remofile can't be easier. It doesn't have many dependencies
and it can all be handled in one command-line.

::

    pip install remofile

I suggest you create a virtual environment before typing this command.
This can easily be done like this.

::

    python3 -m virtualenv python-env
    source python-env/bin/activate

Installing via Pipy provides flexibility as it doesn't have to install
system-wide but you can install from the underlying operating system
package manager as well. Remofile is packaged for various Linux
distributions. Check out the following document.

Run a testing server
--------------------
Before deploying online, better do some **local** tests to famaliarize
yourself with the tool. We'll start with running a local Remofile server
and interact with it.

Remofile doesn't know about users and passwords, instead you use a
token to authenticate.

::

    remofile generate-token

This generates a token which is a 16 letters long string. We'll be using
**qRkVWJcFRqi7rsNMbagaDd** for demonstration purpose. Copy paste and
store yours somewhere as it acts as a unique password.

Just like FTP, you want to jail and expose a directory to multiple
clients. It isn't too hard, the `run` command allows you to do just
that.

::

    mkdir my-directory/
    remofile run my-directory 6768 qRkVWJcFRqi7rsNMbagaDd

It takes the directory (that must be served across the network), the
port (on which to listen) and the previously generated token as
parameters.

This will run a Remofile server which is attached to the current
console. Don't expect this command to return... and don't interupt it!
Now, open another console to continue and work with the server.

.. note::

    There obviously are other ways to start a **Remofile** server, and
    different options too. Notably, the `start` and `stop` commands
    daemonize the proccess.

    Also, if no token is given to the `run` command, one is
    automatically generated and printed out in the connsole before it
    starts.

Before we continue, we must understand an important aspect of Remofile;
its dumb nature. To have an uncomplicated tool to work with, Remofile
makes the assumption that all the files in the folder being served are
readable and writable by the user who started the process. It also makes
the assumption that the directory isn't modified (in any way) by
external mean while it's running. **But that should be common sense,
shouldn't it ?**

By not attempting to be smart, the overall interface and implementation
becomes simpler and easier to deal with. If these two assumptions
aren't respected, Remofile will still graciously fail with proper error
messages.

Shell interactions
------------------
Our next step in experimenting Remofile will be with its command-line
interface. Even though it initially was desgined for integration in
software (from code), it also has a powerful set of command-lines
allowing people to script file operations.

Let's understand the most primitive file operations we can do.

::

    remofile list /

If you're smart enough, you can have an Remofile server online 24/7 and
ditch your USB key. Transfering files across are a few trivail commands
away.

Upload and download files
-------------------------
Things get interesting when we actually get some files transfered to
and from the remote directory. The two main commands involved are
`upload` and `download`. They both support a dozen of options to
customize the behavior.

Both commands can transfer an **individual file**, a **directory** (if
the recursive flag is passed) or a **set of files** specified by a
shell glob patterns.

::

    remofile upload single-file.txt /
    remofile upload a-directory/    /
    remofile upload **/some-text-files*.txt /

    remofile download single-file.txt .
    remofile download a-directory/    .
    remofile download **/some-text-files*.txt .

We notice that the first argument refers to the source files, and the
second argument refers to the destination. The destination must
imperatively be an existing directory on either the remote directory for
the upload command, or the local filesystem for download command.

In fact, the destination directory is optional and is defaulted to the
root directory for the upload command, and the current working directory
for the download command. For instance, you can upload a file, then
download it back without thinking too much

    remofile upload ubuntu-16.04.3-desktop-amd64.iso
    remofile download ubuntu-16.04.3-desktop-amd64.iso

To be written.

This is very close to a front-end to the `upoad_files` and
`download_files` method of the programming API.

Synchronizing directories
-------------------------
To be written.

API Interface
-------------
To be written.

Securing your server
--------------------
Securing your server with private and public keys.

To be written.

Server as a deamon or service
-----------------------------
Foobar.
