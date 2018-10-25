Design Decisions
================
This document presents **Remofile** from the creator perspective and
justifies the software design decisions that were taken all along the
development.

- Reinventing the wheel
- A simpler concept
- File ownership, permissions and timestamp
- Not tuned for performance
- Upcoming improvements

Reinventing the wheel
---------------------
Transferring files is not new; it's an essential need since the
beginning of the Internet. Our options when it comes to transferring
files are FTP and their variant (or even HTTP), usually tunneled
through SSH for security. But those are ancient, sophisticated, and
overly complicated solutions in most situations. For instance, if you
are creating a client-server software and need to transfer files
between multiple endpoints, how do you use FTP (and its hundreds of
tools and libraries out there) in without making the code of your
software ugly and over-complicated. No surprise that
most application prefer roll their own mini-solution by re-implementing
basic file transfer operations on top of other protocols. [#0]_ [#3]_

A modern and lightweight alternative to FTP would be a better fit  when
simply uploading and downloading a couple of files, or synchronizing
directories is needed. Doing these essential file operations should be
effortless in 2018, either at a command-line level or programming level.
This is why Remofile "reinvents the wheel", with a simpler
implementation and a much nicer interface for both sides, client and
server.

A simpler concept
-----------------
Remofile is not much different from FTP in terms of concept; it jails
a given directory on the server side and exposes it to the client. But
unlike FTP, it does it with few differences.

- There is no concurrent connections
- There is no complex authentication system
- There is no changing file owners and permissions
- It's done with less performance and optimizations concerns
- There is no multiple communication channels

It results into a simpler tool closer to the real-world needs. Less
headache as it's easier to grasp, and also results in saner and more
maintainable code on the developer side. Let me elaborate.

One, and only one, client at a time can interact with the remote
directory. Not only it **greatly** simplifies the protocol and the
implementation as it doesn't have to deal with possible unpredictable
conflicts, but it also removes a non-safe practice. Think about it, how
can you reliably make changes and ensure correctness if someone else is
allowed to make changes (at the same time) that can possibly mess with
yours; you'd rather wait until they disconnect before making your
changes. The concept of concurrent access is by nature confusing and
flawed (if it doesn't come with a higher access policy).

Instead of a users with password authentication system, it simply uses
a passphrase, referred as **token**, which the client must know to
access the remote directory. In other words, it's a sort of unique and
global password. If you think a minute, multiple user authentication is
hardly-ever needed because if a folder is shared, users are trusted and
we are aware of the consequences. And most of the time it's not even
shared across different users, but rather across different services,
often owned by a single user. Tokens are easier to work with and is
closer to real-life needs. There's not even a username to remember! And
if the token is compromised, just reset it and redistribute it.

File ownership, permissions and timestamp
-----------------------------------------
This simpler concept jostles a bit with the traditions when transferring
files and it has to do with file ownership, permissions and timestamps.
In fact, those "details", who aren't always important, are needed. But
since Remofile isn't using the server's underlying OS system users to
authenticate clients (unlike FTP), what happens when a file is
transferred, who owns it, what permissions it gets, and how about the
timestamp ?

To keep things simple, and to avoid bloating the interface, both clients
and servers are responsible for their local file-system for the reading
and writing access of their files on each side. When a file is
transferred from one point to another, it gets the local user ownership.
A Remofile server can be started with a given system user and will
assume it has access to all files present in the directory it's serving.

As for file permissions, a file always is readable and writable by the
user, but not executable (unless it's a directory of course). The group
and public permissions are defined by the configuration of the client or
the server.

Not tuned for performance
-------------------------
My primary focus when writing Remofile was **reliability** because how
would it be like if files are corrupted, and **maintainability** because
dealing with transferring files and an internet protocols is actually
difficult in the sense that it can become tricky. The other objectives
were to achieve scriptability and embeddability easiness. The rest, such
as performances and optimized implementation can be improved later.

As such, I preferred to sick with a "dumb" and straight-forward
implementation that assumes the file-system isn't changing by a third
process, and relies on existing high-level tools to do the job. For
instance, it uses **ZeroMQ** for TCP communication and more precisely
the REP-REQ pattern even if it's far from the most efficient to transfer
files across a network. [#1]_ It uses the Python standard library for
its high-level API (the :py:mod:`pathlib` module) to deal with path and
files, as well as its ability to serialize and de-serialize Python
objects (see :py:mod:`pickle` and :py:mod:`marshal` module) and thus
simplifies dealing with data sent across the network.

Implementing a FTP-like solution (that actually does more [#2]_) is a
lot of work for a single person and this is why I didn't focus on
performance. Luckily, in 2018, with our powerful machines and fast
lines, this is not a problem for most scenarios, and is a very
acceptable solution. From another perspective, even if not tuned for
performance, we can say it's faster as it costs less to implement and
maintain Remofile code.

Also note that the implementation will be improved over time to compress
data and evolves into a more optimized solution.

Upcoming improvements
---------------------
Initially, I created the protocol and programming interface of Remofile
as part of another software which needed file transfer features. And
because I felt like this is reinventing the wheel, it slowly evolves
into a project on its own. Here are two important features which weren't
needed by the former software but would enhance greatly Remofile.

* Resuming interrupting file transfers
* Direct read/write file in Python code

See the :doc:`roadmap </roadmap>` document for more information about
features and improvements.

.. [#0] Gitlab Runner, Buildbot, Jenkins and most CI services have custom code to transfer source code back and forth.
.. [#1] Usually, when it comes to transferring files, one would use a lower-level solution that directly deals with streams of bytes.
.. [#2] See its synchronization features and its ability to resume interrupted file transfers.]
.. [#3] Joe Armstrong, creator of Erlang, complains about FTP and write his own quick solution: http://armstrongonsoftware.blogspot.com/2006/09/why-i-often-implement-things-from.html
