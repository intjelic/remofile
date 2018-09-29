Roadmap
=======
While Remofile already achieves its objectives and does perfectly what
it claims to be, I still have a few things in mind. This document lists
the improvements I'd like to make and the features I'd like to add.

.. note::

  If you're using Remofile in production and need to have a feature
  added or need a more efficient implementation, you can still reach me
  and we will see what we can do.

Here is the list of features and improvements altogether (sorted by
priority).

- Warn when the server is in used
- Resume interrupted file transfers
- Direct remote file I/O operations
- Compress large files when transferring
- More efficient transfer implementation
- Depythonization of the Remofile protocol

I'm elaborating on each feature and improvement down below. Feel free
to add your grain of salt on the issue tracker (there's a ticket for
each of them). You can even implement a feature yourself if want to
contribute.

Warn when the server is in used
---------------------------------------
By design, simultaneous access to the Remofile server is not allowed.
However, connecting to the server while it's currently use by somebody
else will result in the connection hanging.

There should be a proper authentication system that warns user when
trying to connect when the server is in used.

Resume interrupted file transfers
---------------------------------
Interrupted file transfers are annoying when dealing with large files.
Even though implementing this feature isn't technically a challenge, it
does require to adapt the protocol. Also various decisions must be taken
such as where do the interrupted file data resides (left in the remote
directory itself, or saved in a temporary directory?) and others. As
soon as I've got some time for that, I'll get down to it.

Direct remote file I/O operations
---------------------------------
Another feature that could be useful is direct opening of remote file
in Python code. Basically, one would open a remote file using the
`open()` function and reading and writing would happen transparently.
Also, with the new `pathlib` module, we can also imagine implementing a
`RemofilePath`.

Compress large files when transferring
--------------------------------------
Optimizing transfer of large files by compressing them is one (easy)
step towards a more efficient implementation.

The idea came to me after looking at the FTP client options. I should
investigate the `-z`, `--compress` and `--compress-level=NUM` that
allows to compress file data during the transfer and explicitly set a
compression level.

More efficient transfer implementation
--------------------------------------
The current implementation is dumb. In fact, it's really dumb because I
was rushing an implementation that works, and was focusing on a quality
programming interface quality that wouldn't change. Luckily, with the
high-bandwidth connection we have nowadays, the current implementation
is probably acceptable for most use cases. But some effort could be made
in that direction.

For now, all the work is entirely done with a single pair of REQ-REP
socket for simplicity. Transferring large files will result in a huge
amount of unnecessary requests from the client (see the protocol
specifications document to understand why). The protocol could be
updated to use a pair of streaming socket (or whatever their name, I'm
not a ZeroMQ expert) after a large file is 'accepted' and its transfer
initiated, to transfer the file chunks over.

Depythonization of the Remofile protocol
----------------------------------------
Check out the protocol specifications document and you'll quickly see it
relies on the Python bindings of ZeroMQ which itself relies on
serialization Python objects.

I'd like to make some improvements to the protocol to make it more
'binary' oriented (and thus, not specific to a given programming
language), so one day, somebody (me ?) could make Remofile available to
C/C++ level.
