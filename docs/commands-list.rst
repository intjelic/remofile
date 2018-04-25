Commands List
=============

This document is the reference of the command-line interface provided by
**Remofile** to start a server and perform various file operations from
a shell. Commands are divided into client-related commands and
server-related commands.

Client-related commands
-----------------------

The client-related commands all relies on the shell environment variables to locate the remote server and do the authentication process. Improperly configured environment will result in a premature stop.

**REMOFILE_HOSTNAME**

This is the address of the Remote server.

**REMOFILE_PORT**

By default, it listens to 6768.

**REMOFILE_TOKEN**

Foobar.

**REMOFILE_PUBLIC_KEY**

Foobar.

.. click:: remofile.cli:cli
   :prog: remofile
   :show-nested:

Server-related commands
-----------------------

.. click:: remofile.cli:cli
   :prog: remofile
   :show-nested:
