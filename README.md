# Remofile

Remofile is a **protocol**, a **Python library** and a **command-line interface** to transfer files back and forth from/to a remote server. It's an **easy-to-use** and **embeddable** alternative to FTP and other transfer files tools.

It features:

* All common file operations
* Simple authentication based on tokens
* Encrypted communication based on Curve
* Pick up interrupted transfered files
* Bidirectional directory synchronization
* Direct remote file reading and writing
* Listening on a custom ZeroMQ socket

Because it's purposely designed to be simple, it doesn't support concurrent access, changing ownerships and permissions, soft or hard symbolic links or any complex authentication system. However, it's secured and Remofile will also be an excellent files **synchronization** tool later.

## Why reinventing the wheel ?

Transferring files is not new; it's an essential need since the beginning of the Internet. Our options when it comes to transferring files are FTP and their variant (or even HTTP), usually tunneled through SSH for security. But those are ancient, sophisticated, and overly complicated solutions to set up or embed in a custom software. No surprise that most application prefer reimplementing basic file transfer operations on top of their own protocol.[1]

Having a modern and lightweight alternative to FTP can be a huge relieve when we have simple needs such as listing files, uploading and downloading files, or creating and deleting files or directories. Doing these basic file operations should be effortless either at a command-line level or software level. This is why Remofile "reinvents the wheel", with a simpler implementation and a much nicer interface for both side client and server.

As a downside, it's not tuned for performance, in fact, the implementation is pretty dumb and anticipate little... but it does the job and with class.

## How does it work ?

The concept of Remofile is to serve one directory over TCP in a **one to one** client-server architecture. The directory is called the **served directory** (or remote directory) and is said jailed; the client accessing it can't access the entire file system.

Instead of an entire authentication system, it's designed to work for only one client at time and with just a **token** in hand (a sort of of key acting as a password) to access the served directory. It's purposely not designed for concurrent access, simplifying a lot the implementation and the protocol.

On top of that, Remofile implements a command-line interface that reflects standard Linux command-lines like `ls`, `rcp`, `mkdir`, `rm`. 

## Real-life examples

Configure the environment variables and you're ready to go.

```
export REMOFILE_SERVER=localhost:6768
export REMOFILE_TOKEN=TTA3rMB8VtNYv25kdipkaJ

remofile list /
remofile directory my-os-isos /
remofile upload ubuntu-16.04.3-desktop-amd64.iso /
remofile remove /my-os-isos/ubuntu-16.04.3-desktop-amd64.iso
```

The example was self-explanatory for any Linux user and you're expected to understand it.

Foobar.

- See an example of to start a client and a server in a Python code.
- See an example of how to start a stand-alone server.
- See an example of the command-line interface.

The following examples shows how to set up a server serving a directory 'MyRemoteDirectory' and a client uploading an ISO file 'ubuntu-16.04.3-desktop-amd64.iso' to it.

The server code.

```python
from remofile import FileServer, generate_token

token = generate_token()

server = FileServer('~/MyRemoteDirectory', token)
server.run('localhost', 6768)
```

The client code.
```python
from remofile import FileClient

client = FileClient('localhost', 6768, token)
client.upload('ubuntu-16.04.3-desktop-amd64.iso', '/')
```

There were programming examples in Python, but you can also set up an independent **Remofile** server without writing code. The manual covers this topic in details.

## For more information

Foobar.