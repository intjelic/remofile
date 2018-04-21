Commands List
=============

**CLI Reference**

This document is the reference of the command-line interface provided by **Remofile** to start a server and perform various file operations from a shell. Commands are divided into client-related commands and server-related commands.

## Client-related commands

The client-related commands all relies on the shell environment variables to locate the remote server and do the authentication process. Improperly configured environment will result in a premature stop.

**REMOFILE_HOSTNAME**

This is the address of the Remote server.

**REMOFILE_PORT**

By default, it listens to 6768.

**REMOFILE_TOKEN**

Foobar.

**REMOFILE_PUBLIC_KEY**

Foobar.

### The `list` command

**NAME**

`remofile-list` - To be written.

**SYNOPSIS**

`remofile list [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a client-related command that does something. To be written.

**OPTIONS**

To be written.

**EXAMPLES**

To be written.

### The `file` command

**NAME**

`remofile-file` - To be written.

**SYNOPSIS**

`remofile file [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a client-related command that does something. To be written.

**OPTIONS**

To be written.

**EXAMPLES**

To be written.

### The `directory` command

**NAME**

`remofile-directory` - To be written.

**SYNOPSIS**

`remofile directory [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a client-related command that does something. To be written.

**OPTIONS**

To be written.

**EXAMPLES**

To be written.

### The `upload` command

**NAME**

`remofile-upload` - To be written.

**SYNOPSIS**

`remofile upload [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a client-related command that does something. To be written.

**OPTIONS**

To be written.

**EXAMPLES**

To be written.

### The `download` command

**NAME**

`remofile-download` - To be written.

**SYNOPSIS**

`remofile download [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a client-related command that does something. To be written.

**OPTIONS**

To be written.

**EXAMPLES**

To be written.

### The `remove` command

**NAME**

`remofile-remove` - To be written.

**SYNOPSIS**

`remofile remove [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a client-related command that does something. To be written.

**OPTIONS**

To be written.

**EXAMPLES**

To be written.

## Server-related commands

Foobar.

### The `run` command

**NAME**

`remofile-run` - Start a non-daemonized sever.

**SYNOPSIS**

`remofile run [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a server-related command that start a non-daemonized server (not detached from the shell). The directory parameter is the root directory which will be served and therefore must be an existing directory. The server listens on port 6768 by default but it can be changed with the port parameter. If the token is not specified, it's generated and printed out to the console before the server starts running.

Additionally, the file size limit and the chunk size range can be altered. The file size limit and minimum chunk size must be both be greater than 0, and maximum chunk size must be greater or equal to minimum chunk size.

**OPTIONS**

--file-size-limit
   Prevent transferring files that exceed the given file size limit.

--min-chunk-size
   Prevent transferring files if the chunk size is too small.

--max-chunk-size
   Prevent transferring files if the chunk size is too big.

**EXAMPLES**

You can quickly start a Remofile server that serves `my-directory/` on port **6768** with the following command-line.

```
mkdir my-directory
rmf run my-directory/ 6768 my-custom-token
```

Refer to the client-related commands to start interacting with the served directory.

### The `start` command

**NAME**

`remofile-start` - Start a daemonized sever.

**SYNOPSIS**

`remofile start [OPTIONS] DIRECTORY [PORT] [TOKEN]`

**DESCRIPTION**

This is a server-related command that start a daemonized server (detached from the shell). Unlike the run command, it accepts the `--pidfile` flag which tells the pidfile location. By default, the pidfile is created in the current working directory and named 'daemon.pid'.

Refer to the run command for more information.

**OPTIONS**

--pidfile
   Location of the pidfile. By default, it assumes 'daemon.pid' in the current working directory.

--file-size-limit
   Prevent transferring files that exceed the given file size limit.

--min-chunk-size
   Prevent transferring files if the chunk size is too small.

--max-chunk-size
   Prevent transferring files if the chunk size is too big.

**EXAMPLES**

You can quickly start a Remofile server that runs in the background (you can close the shell) and that serves `my-directory/` on port **6768**, with the following command-line.

```
mkdir my-directory
rmf run my-directory/ 6768 my-custom-token
```

Refer to the stop command to stop the server.

### The `stop` command

**NAME**

`remofile-stop` - Stop a daemonized server.

**SYNOPSIS**

`remofile stop [OPTIONS]`

**DESCRIPTION**

This is a server-related command that stop a daemonized server from its pidfile. By default, it expects the pidfile in the current working directory with the name 'daemon.pid' but it can be altered with the `--pidfile` flag.

**OPTIONS**

--pidfile
   Location of the pidfile. By default, it assumes 'daemon.pid' in the current working directory.

**EXAMPLES**

You can stop a Remofile server that has previously been started with the start command in the same directory, with the following command-line.

```
remofile stop
```

With the `--pidfile` flag, you can run this command from any directory if you specify the pidfile location.
