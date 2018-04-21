The User Guide
==============
.. toctree::
   :hidden:

.. warning::

    The user guide is still fairly incomplete. Expect some serious
    update in the upcoming weeks.

The user guide gets you started with using Remofile. It covers the
installation and the principles. For more exhaustive documentation,
refer to the respective documents (the :doc:`commands list
</commands-list>`, the :doc:`API reference </api-reference>`, the
:doc:`protocol specifications </protocol-specifications>`)

* Easy installation
* Run a testing server
* Shell interactions
* Synchronizing directories
* Standalone server

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

Foobar.

Run a testing server
--------------------
Before deploying online, better do some local tests to famaliarize
yourself with the tool.

Remofile doesn't know about users and passwords, instead you use a
token to authenticate.

::

    remofile generate-token

This generates a token like the following `qRkVWJcFRqi7rsNMbagaDd`. Copy
paste and store it somewhere as it acts as a unique password.

Just like FTP, you want to jail and expose a directory to a client. It
isn't too hard to do, just use the `run` command.

::

    mkdir my-directory/
    remofile run my-directory 6768 qRkVWJcFRqi7rsNMbagaDd

This will run a Remofile server which is attached to the current
console. Don't interupt it and open another console.

.. note::

    Remofile makes the assumption that all the files in the folder is
    readable and writable and that it isn't modified in any way by
    other processes while it's running.

Shell interactions
------------------
Even thought Remofile was initially desgined for integration in
software, it also has a powerful set of command-lines allowing people
to script file operations.

To be written.

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
