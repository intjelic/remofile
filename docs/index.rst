Remofile : Alternative to FTP
=============================

.. toctree::
   :hidden:

   getting-started
   api-reference
   cli-reference
   protocol-specifications
   design-decisions
   roadmap

   old-commands-list

.. warning::

    Remofile is still in development. Please give me your feedbacks to
    dewachter[dot]jonathan[at]gmail[dot]com.

.. image:: https://img.shields.io/pypi/v/remofile.svg
    :target: https://pypi.python.org/pypi/remofile

.. image:: https://img.shields.io/pypi/l/remofile.svg
    :target: https://pypi.python.org/pypi/remofile

.. image:: https://img.shields.io/pypi/pyversions/remofile.svg
    :target: https://pypi.python.org/pypi/remofile

.. image:: https://readthedocs.org/projects/remofile/badge/?version=latest
    :target: http://remofile.readthedocs.io/en/latest/?badge=latest

Remofile is a **protocol**, a **Python library** and a **command-line
interface** to transfer files back and forth from/to a remote server.
It's a **quick** and **easy-to-use** alternative to FTP and other
transfer files tools.

.. note::

    Remofile doesn't claim to be better than FTP but rather offers a
    better solution for developers in most situations as it's
    purposely designed for easier use and integration, At the end, it
    does the same work but with a saner and more maintainable code on
    the developer side.

    See this :doc:`document </design-decisions>` for more details.

It's also properly documented and heavily tested. Check out the
:doc:`user guide </getting-started>` to get you started with using Remofile.

Remofile is... quick
^^^^^^^^^^^^^^^^^^^^
It doesn't take much time and effort to get a Remofile server running.

.. code-block:: shell

    mkdir my-shared-directory
    remofile run my-shared-directory/ 6768 qRkVWJcFRqi7rsNMbagaDd

Directory `my-shared-directory/` is now jailed and accessible over the
network on port 6768 with the token `qRkVWJcFRqi7rsNMbagaDd`.

.. note::

    There are other ways to start a server and different options. They
    are all covered in the :doc:`documentation </getting-started>`.

Remofile is... easy-to-use
^^^^^^^^^^^^^^^^^^^^^^^^^^
It's straightfoward to interact with the remote directory; no connection
step is required, just configure the shell environment and you are ready
to go.

.. code-block:: shell

    export REMOFILE_HOSTNAME=localhost
    export REMOFILE_PORT=6768
    export REMOFILE_TOKEN=qRkVWJcFRqi7rsNMbagaDd

    remofile upload --progress ubuntu-16.04.3-desktop-amd64.iso /

This uploads the local file *ubuntu-16.04.3-desktop-amd64.iso* to the
remote directory. It may take time to complete the operation, this is
why the **\--progress** flag is set to display a progress bar.

For even more accessebility, add the first 3 lines to your `.bashrc` and
you can now interact with the remote directory from anywhere and
anytime.

.. note::

    Replace localhost with the actual IP or the domain name to access
    the remote Remofile server. Ensure the port is open on the server
    side too.

Remofile is... powerful
^^^^^^^^^^^^^^^^^^^^^^^
Remofile features all common file operations indeed. On top of that, it
also comes with bidirectional synchronization. You can synchronize
directories the same way you woud do with `rsync`.

.. code-block:: shell

    # synchronize the local 'foo' directory with the remote 'bar' directory
    remofile sync local  foo /bar

    # synchronize the remote 'bar' directory with the local 'foo' directory
    remofile sync remote foo /bar

In upcoming releases, Remofile will be able to resume interupted file
transfers, and transparently read/write remote files in a Python code.

.. note::

    Please, consider Remofile is young and is still somewhat in
    development. Check out the :doc:`roadmap </roadmap>` to understand
    what is still to be implemented.

Remofile is... scriptable
^^^^^^^^^^^^^^^^^^^^^^^^^
With its "connectionless" command-line interface, Remofile becomes
highly scriptable. See the bunch of commands availabe akin to `ls`,
`touch`, `mkdir` and `rm`.

.. code-block:: shell

    # list files the remote (root) directory
    remofile list /

    # create a directory then a file in the remote directory
    remofile directory foo /
    remofile file      bar /foo

    # delete the file and the directory we just created
    remofile remove /foo/bar
    remofile remove /foo

The command-line interface might feel odds for now but it will likely
change later to feel more natural. See the :doc:`commands list </cli-reference>`
learn how to use the command-line interface.

Remofile is... embeddable
^^^^^^^^^^^^^^^^^^^^^^^^^
Remofile primarily is a **Python library** to run servers and interact
with the remote directory from the code. It's an ideal solution when you
write client-server software that needs to tranfer files to multiple
endpoints.

.. code-block:: shell

    from remofile import Client, synchronize_upload

    client = Client('localhost', 6768, 'qRkVWJcFRqi7rsNMbagaDd')
    synchronize_upload(os.getcwd(), '/')

The remote directory is now synchronized with the current working
directory in the most painless fashion.

.. note::

    Because it's based on **ZeroMQ**, you can even configure the server
    with your own ZeroMQ socket and reduces the need to open an
    additional port.

Remofile is... uncomplicated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Remofile was purposely written  and leave hundreds of features
that we usually don't need. The result is an uncomplicated software that
we're happy to work with.

.. warning::

    To be written.

Remofile is... secure
^^^^^^^^^^^^^^^^^^^^^

.. warning::

    To be written.
