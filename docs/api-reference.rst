API Reference
=============

This document is the API reference of Remofile. All classes, functions
and exceptions are accessible from a single import of the `remofile`
package.

.. code-block:: python

    from remofile import *

The programming interface is essentially made of two classes which are
:py:class:`Client` and :py:class:`Server`. They implement both side of
the Remofile :doc:`protocol </protocol-specifications>`.

Interface overview
------------------

The client class implements all primitive file operations and therefore
any more complex file operations can theorically be implemented on top
of it.

* :py:meth:`list_files`
* :py:meth:`create_file`
* :py:meth:`make_directory`
* :py:meth:`upload_file`
* :py:meth:`upload_directory`
* :py:meth:`download_file`
* :py:meth:`download_directory`
* :py:meth:`delete_file`

However, the algorithm module already implements a couple of
useful more advanced file operations for you. For instance, it can
upload and download trees of files, understand glob patterns and handle
conflicts. It also has functions to synchronize directories from client
to server and server to client. These functions are all exposed.

* :py:func:`upload_files`
* :py:func:`download_files`
* :py:func:`synchronize_upload`
* :py:func:`synchronize_download`

Dealing with errors is an important aspect in a code that involves file
operations. A set of exceptions are defined and they all have the
:py:exc:`RemofileException` exception as base class. Therefore, you can
catch all Remofile-related exceptions in one statement.

.. code-block:: python

    try:
        do_file_operation()
    except RemofileException:
        deal_with_exception()

Addtionally, some helper functions like :py:func:`generate_token` and
:py:func:`is_file_name_valid` are also exposed.

Two main classes
----------------

.. py:currentmodule:: remofile

.. autoclass:: Client

    .. automethod:: __init__

    .. automethod:: list_files
    .. automethod:: create_file
    .. automethod:: make_directory
    .. automethod:: upload_file
    .. automethod:: upload_directory
    .. automethod:: download_file
    .. automethod:: download_directory
    .. automethod:: delete_file

.. autoclass:: Server

    .. automethod:: __init__
    .. automethod:: run
    .. automethod:: terminate

Advanced algorithms
-------------------
Not that advanced since most code will want to use these functions
rather than the primitive ones provided by the :py:class:`Client` class
(unless your code work is garanteed to run in a clean environment). They
do more or less the same task but it does it with much more flexibility
and is more tolerant to file conflicts; ideal for code that runs more
than once with variation in the environment.

.. autofunction:: upload_files
.. autofunction:: synchronize_upload
.. autofunction:: download_files
.. autofunction:: synchronize_download

Handling exceptions
-------------------
The set of exceptions implemented by Remofile deserves some
explainations. More precisely, one need (or need not) to understand
the difference betweeen UnpexectedError, UnknownError and
BadRequestError

BadRequestError should never occur with an updated client as it
implements the protocol. Those are raised when it's known misuse of the
protocol and the server detected it.

UnexpectedError exceptions are likely to occur when the assumptions

UnknownError are all other exceptions that might occurs. For instance,
an error occurs on the server side and is unable For instance, if
the server response with unknown data. Or

.. autoexception:: RemofileException

.. autoexception:: SourceNotFound
.. autoexception:: DestinationNotFound

.. autoexception:: InvalidFileName
.. autoexception:: FileAlreadyExists

.. autoexception:: UnexpectedError
.. autoexception:: BadRequestError
.. autoexception:: UnknownError
.. autoexception:: CorruptedResponse

Helper functions
----------------

.. autofunction:: generate_token
.. autofunction:: is_file_name_valid
