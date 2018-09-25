Protocol Specifications
=======================
This document defines the protocol used in **Remofile** that clients use
to transfer files back and forth from/to the remote server.

- Request and response pattern
- The four transferring states
- Error and refused responses
- File name validity
- Absolute and relative directory
- List files request
- Create file request
- Make directory request
- Upload request-response cycle
- Download request-response cycle
- Delete file resquest

See `client.py`_ and `server.py`_ source file for an example of the
implementation of this protocol.

.. _client.py: https://github.com/sonkun/remofile/tree/master/remofile/client.py
.. _server.py: https://github.com/sonkun/remofile/tree/master/remofile/server.py

.. glossary::

   valid file name
      This is the description of valid file name term.

::

    Todo:
    - talk about timeout (stateless connection), immediate consequence of the underlying ZeroMQ protocol
    - talk about authentication and encryption
    - talk about zeromq socket identity
    - talk about timeout
    - talk about authentication and encryption

Request and response pattern
----------------------------
The protocol is entirely based on **ZeroMQ** using one pair of socket in
the **REQ-REP** mode. Documenting and understanding becomes easy because
the client and the server are locked in a two steps communication
pattern; the client sends one **request** and the server sends back one
**response**. Additionally, all responses may come along with a
**reason**.

The list of possible requests.

- LIST_FILES
- CREATE_FILE
- MAKE_DIRECTORY
- UPLOAD_FILE
- SEND_CHUNK
- DOWNLOAD_FILE
- RECEIVE_CHUNK
- CANCEL_TRANSFER
- REMOVE_FILE

The list of possible responses.

- ACCEPTED
- REFUSED
- ERROR

The list of possible reasons.

- FILE_LISTED
- FILE_CREATED
- DIRECTORY_CREATED
- INVALID_FILE_NAME
- FILE_NOT_FOUND
- FILE_ALREADY_EXISTS
- NOT_A_FILE
- NOT_A_DIRECTORY
- INCORRECT_FILE_SIZE
- INCORRECT_CHUNK_SIZE
- TRANSFER_ACCEPTED
- CHUNK_ACCEPTED
- CHUNK_SENT
- TRANSFER_COMPLETED
- TRANSFER_CANCELLED
- BAD_REQUEST
- UNKNOWN_ERROR

Requests and reasons are **Python tuple** whose first element is a
**request type** for requests, or **response type** for responses.
Information related to the request or response compose the rest of the
tuple. The tuple and the elements in it are serialized and sent over
using the `send_pyobj()` and `recv_pyobj()` method. Refer to the
**pyZMQ** documentation to understand the serialization process.

The four transferring states
----------------------------
There are four transferring states in which the server can be and they
condition the possible responses to a request. These states are
**exclusive**; the server is at one of those states at a time.

The four transferring states.

- IDLE
- UPLOAD
- DOWNLOAD
- DELETE

At connection time, the transferring state always is **IDLE** and
because it's a one to one network architecture, the client is expected
to be aware of the server's current state at any time; there is no
getter to know the current transferring state.

Some file operations can take long to complete and the transferring
states allow to model their processing time. For instance, uploading
will happen in several request-response cycles when the server is
marked in the **UPLOAD** transferring state. Unrelated requests to
uploading a file during this process obviously are errors.

Error and refused responses
---------------------------
The difference between a **REFUSED** and **ERROR** response lies in the
*correct usage of the protocol* and *the expected behavior*.

Regardless of the current business, the client is expected to
communicate **flawlessly** with the server in a known language and the
server is expected to deal with all possible errors that may happen
during the fulfillment of the rquest... and reply with an ACCEPTED or
**REFUSED** response.

If the client sends a bad request, this is an **ERROR** because it
failed to follow the protocol specifications. If an unexpected error
occurs on the server side, this is an **ERROR**. All other events such
as a failure to complete a request because of possible unmet runtime
conditions are **not** errors.

We also notice that there are only two possible error responses; bad
requests and unknown errors. Unknown errors come along with a message
describing the error. Theoretically, all requests may return an
**ERROR** response.

File name validity
------------------
The name of the file must be valid which is any sequence that doesn't
contain one the following forbidden character.

- <
- \>
- :
- /
- \\
- \|
- ?
- \*

Abc.

Absolute and relative directory
-------------------------------
Unlike the local filesystem, there is no notion of **current working
directory** when working with the remote directory exposed by Remofile.

As a direct consequence, all paths that refer to the remote directory
should be absolute paths. If relative paths are given to the server, an
implementation can be tolerant and constructs an absolute paths out of
the relative paths by combining them to the root directory.

List files request
------------------
Listing files is the only request that can be made regardless of the
current transferring state. It's a non-lasting operation that should be
canceled on the client side with a timeout value if ever the server
takes long to reply.

The **LIST_FILES** request is contructed with the path to the directory
to list files for.

Request example:

.. code-block:: python

    request = (Request.LIST_FILES, '/foo/bar')

This will list the `/foo/bar` directory and compute their metadata if
the request is accepted. Metadata is a tuple that includes a boolean
indicating whether the file is a directory or not, the size of the file
(the value is 0 in case of directory) and the last modification time of
the file.

.. code-block:: python

    response = (Response.ACCEPTED, Reason.FILE_LISTED,
        {'foo.bin' : (False, 423, 4687421324), 'bar' : (True, 0, 1654646515)})

The path to the directory to list files for must be an absolute path
that refers to an **existing directory**. Possible refuse reason is
**NOT_A_DIRECTORY** if this directory doesn't exist.

Another response include **BAD_REQUEST** error response if the directory
to list files for isn't an absolute path.

Create file request
-------------------
Creating a file can only happen when the file server is in the **IDLE**
state. It's a non-lasting operation that should be canceled on the
client side with a timeout value if ever the server takes long to reply.

The **CREATE_FILE** request is constructed with the **name of the file**
to be created followed by the **destination directory**.

Request example.

.. code-block:: python

    request = (Request.CREATE_FILE, 'qaz.bin', '/foo/bar')

This will create an empty file with name `qaz.bin` in `/foo/bar`
directory if the request is accepted.

Response example.

.. code-block:: python

    response = (Response.ACCEPTED, Reason.FILE_CREATED)

The name of the file must be :term:`valid file name` that doesn't
conflict with an existing file (or directory) in the destination
directory. The destination directory must be an absolute path of an
**existing directory**.

Possible refuse reasons.

* **INVALID_FILE_NAME** when the file name isn't valid
* **NOT_A_DIRECTORY** when the destination directory doesn't exist
* **FILE_ALREADY_EXISTS** when it conflicts with an existing file (or directory)

Another response include **BAD_REQUEST** error response if the
destination directory isn't an absolute path.

Make directory request
----------------------
Creating a directory can only happen when the file server is in the
**IDLE** state. It's a non-lasting operation that should be canceled on
the client side with a timeout value if ever the server takes long to
reply.

The **MAKE_DIRECTORY** request is constructed with the **name of the
directory** to be created followed by the **destination directory**.

Request example.

.. code-block:: python

    request = (Request.MAKE_DIRECTORY, 'qaz', '/foo/bar')

This will create an empty directory with name `qaz` in `/foo/bar`
directory if the request is accepted.

Response example.

.. code-block:: python

    response = (Response.ACCEPTED, Reason.DIRECTORY_CREATED)

The name of the directory must be :term:`valid file name` that doesn't
conflict with an existing directory (or file) in the destination
directory. The destination directory must be an absolute path of an
**existing directory**.

Possible refuse reasons.

* **INVALID_FILE_NAME** when the directory name isn't valid
* **NOT_A_DIRECTORY** when the destination directory doesn't exist
* **FILE_ALREADY_EXISTS** when it conflicts with an existing directory (or file)

Another response include **BAD_REQUEST** error response if the
destination directory isn't an absolute path.

Upload request-response cycle
-----------------------------
Initiating an upload will turn the server into **UPLOAD** state and it
can only be requested when the server is in **IDLE** mode. Transfers is
interrupted in the middle if an error occurs on the server side, or can
be explicitly interrupted on request by the client.

The three requests involved in uploading files are.

- UPLOAD_FILE
- SEND_CHUNK
- CANCEL_TRANSFER

The **UPLOAD_FILE** request initiates the uploading process and turns
the server into **UPLOAD** state. The subsequent requests must either be
**SEND_CHUNK** to send the file data to the server, or
**CANCEL_TRANSFER** to interrupt the transfer. When the file data is
entirely sent over (when all data chunks are sent) or if the transfer
explicitely interrupted, the server goes back to **IDLE** state.

The upload file request
^^^^^^^^^^^^^^^^^^^^^^^
The **UPLOAD_FILE** request is constructed with the **file name**, the
**destination directory**, the **file size** and the **chunk size**.

Request example.

.. code-block:: python

    request = (Request.UPLOAD_FILE, 'qaz.bin', '/foo/bar', 23735613, 4096)

This request initiates the upload of the file `qaz.bin` (supposedly
located on the client file system) to the `/foo/bar` directory (on the
server side). The file is 23735613 bytes long and has to be transfered
by chunk of 4096 bytes. If the response is accepted, the client and
server have now agreed upon a given cycle of upload request-response.

Response example.

.. code-block:: python

    response = (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED)

The file name must be a :term:`valid file name` that doesn't conflict
with an existing file (or directory) in the destination directory. The
destination directory must be an absolute path to an **existing
directory**. The file size can't be 0 or greater than the maximum set by
the server, and the chunk size must be within the range set on the
server side (by default between 512 and 8192).

Possible refuse reasons.

* **INVALID_FILE_NAME** when the file name isn't valid
* **FILE_ALREADY_EXISTS** when the file to upload conflicts with an existing file (or directory)
* **NOT_A_DIRECTORY** when the destination directory doesn't exist
* **INVALID_FILE_SIZE** when the file size is invalid
* **INVALID_CHUNK_SIZE** when the chunk size is invalid

Another response include **BAD_REQUEST** error response if the
destination directory isn't an absolute path.

The send chunk request
^^^^^^^^^^^^^^^^^^^^^^
The **SEND_CHUNK** request is constructed with the chunk data which is
a byte string with exactly length as initially defined.

Request example.

.. code-block:: python

    request = (Request.SEND_CHUNK, b'F\x8c1\xa4\xb5\xc7')

This will move the upload process one step forward by sending the next
6 bytes (if the chunk size) was set at 6 (unlikely). This writes the
next 6 bytes to the uploaded bytes on the server side if the request
is accepted.

Response example.

.. code-block:: python

    response = (Response.ACCEPTED, Reason.CHUNK_RECEIVED)
    response = (Response.ACCEPTED, Reason.TRANSFER_COMPLETED)



The file size is given for the server to understand when the uploading
process is completed. The chunk size defines how much data is sent per
request-response and therefore will define how many of them.

Example:

.. code-block:: python

    request = {
        'type' : Request.UPLOAD_FILE,
        'destination' : '/my/directory',
        'file-name' : 'myfile',
        'file-size' : 1687365,
        'chunk-size' : 512
    }

After the upload is initiated (the server responded with
**TRANSFER_ACCEPTED**)



 and that means the server is now in **UPLOADING** state and ready to
 receive chunks. This is unless the server replies with one the
 following error response.

- INCORRECT_STATE
- NOT_A_DIRECTORY_ERROR
- FILE_EXISTS_ERROR


The next set of requests (and responses) are repeated **SEND_CHUNK**
that carries the chunk data.
Server reply with CHUNK_ACCEPTED.

The client is expected to send repeatedly chunks of the file data until
the transfer is completed.

SEND_CHUNK
ACCEPTED, CHUNK_ACCEPTED
ACCEPTED, TRANSFER_COMPLETED

In case the client explictely cancel the trasnfer, it sends
CANCEL_TRANSFER
and server replies with,
ACCEPTED, TRANSFER_CANCELLED

In case client sends invalid chunk, the server response
ERROR, BAD_REQUEST
Beware, it will also cancel the current transfer and put the server back
to IDLE state.

In case an error occurs,
ERROR, UNKNOWN_ERROR

Download request-response cycle
-------------------------------

Downloading can only happen when the file server is in the **IDLE** mode.
Initiating a download will turn the server into **DOWNLOAD** state.
Transfer can be interrupted in the middle because of an error on the
server side, or can be explicitly interrupted on the client side.

The three requests involved in downloading files are.

- DOWNLOAD_FILE
- RECEIVE_CHUNK
- CANCEL_TRANSFER

The **DOWNLOAD_FILE** request initiates the downloading process and
turns the server into **DOWNLOAD** state. The subsequent requests are
either **RECEIVE_CHUNK** to receive the file data from the server, or
**CANCEL_TRANSFER** to interrupt the transfer. When the file data is
entirely received (when all data chunks are received) or the transfer
interrupted, the server is put back into **IDLE** state.

The download file request
^^^^^^^^^^^^^^^^^^^^^^^^^
Long description.

Request example.

.. code-block:: python

    request = (Request.DOWNLOAD_FILE, args)

Long description.

Response example.

.. code-block:: python

    request = (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED)

Long description.

The receive chunk request
^^^^^^^^^^^^^^^^^^^^^^^^^
Long description.

Request example.

.. code-block:: python

    request = (Request.RECEIVE_CHUNK, args)

Long description.

Response example.

.. code-block:: python

    request = (Response.ACCEPTED, Reason.CHUNK_SENT)

Long description.

The cancel transfer request
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Long description.

Request example.

.. code-block:: python

    request = (Request.CANCEL_TRANSFER, args)

Long description.

Response example.

.. code-block:: python

    request = (Response.ACCEPTED, Reason.TRANSFER_CANCELLED)

Long description.

.. notes::

    The dowloading state is akin to the uploading state.

    The different with downloading is, instead of sending the file size
    informtion, it's received from the server.

    directory = '/my-software'
    filename = 'Win7.iso'
    chunk_size = 512

    request = (Request.DOWNLOAD_FILE, directory, filename, chunk_size)

    Server returns the actual (optimal?) chunk size to be used.
    Long description.

    response = (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED, chunk_size)


Delete file request
-------------------
To be written.
