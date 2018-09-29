Software Design
===============
This document presents **Remofile** from the creator perspective and
justifies the software design decisions that were taken all along the
development.

- Reinventing the wheel
- A simpler concept
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
tools and libraries out there) in clean way and  without
overcomplicating the architecture of your software. No surprise that
most application prefer reimplementing basic file transfer operations on
top of their own protocol. [#0]_

A modern and lightweight alternative to FTP would be a better fit  when
simply uploading and downloading a couple of files, or synchronizing
directories is needed. Doing these essential file operations should be
effortless in 2018, either at a command-line level or software level.
This is why Remofile "reinvents the wheel", with a simpler
implementation and a much nicer interface for both side client and
server.

A simpler concept
-----------------
Remofile is not much different from FTP in terms of concept; it jails
a given directory on the server side and exposes it to the client. But
unlike FTP, it does it with few differences.

- There is no multi-user connection (concurrent access are unsafe)
- There is no complex authentication system (most case not needed)
- There is no changing file owners and permissions (most case not needed or can be achieved in other ways)
- With less performance and optimizations concerns
- There is no multiple channel (command and binary channels)

It results into a simpler tool closer to the real-world needs. Less
headache as it's easier to grasp, and also results in saner and more
maintanable code on the developer side. Let me elaborate.

One, and only one, client at a time can interact with the remote
directory. Not only it **greatly** simplifies the protocol and the
implementation as it doesn't have to deal with possible unpredictable
conflicts, but it also removes a non-safe practise. Think about it, how
can you reliably make changes and ensure correctness if someone is also
allowed to make changes that can possibly mess with yours; you'd rather
wait until they disconnect before doing your changes. The concept of
concurrent free access is by nature flawed without a strict access
policy.

Instead of a users with password authentication system, it simply uses
a passphrase, reffered as **token**, which the client must know to
access the remote directory. In other words, it's a sort of unique and
global password. If you think a minute, multiple user authentication is
hardly-ever needed because if a folder is shared, users are trusted and
we are aware of the consequences. And most of the time it's not even
shared across different users, but rather across different services,
often owned by a single user. Tokens are easier to work with and closer
to real-life needs. There's not even a username to remember! And if the
token is compromised, just reset it and redistribute it.

Indirectly, not integrating Remofile access with the OS system users
impacts the concept of file owners. It's a feature I didn't want because
it's in most case unneeded again and complicates the tool quite a lot.
I replaced it with a much simpler concept. Both client and server are
responsible for their local filesystem to be able to read and write the
files they want to deal with. When a file is transfered from one point
to another, it gets the local user ownership. A Remofile server can be
started with a given user and assumes it has access to all files
present in the directory it's serving.

As for the permissions, a file always is readable and writable by the
user, but not executable (unless it's a directory of course). The group
and public permissions are defined by the configure of the client or
the server.

Not tuned for performance
-------------------------
My primary focus when writing Remofile was **reliability** because how
would it be like if files are corrupted, and **maintainability** because
dealing with files and an internet protocol involes dealing with
hundreds of nasty foobar. The other objectives were to fulfill
scriptability and embeddability easiness. The rest, such as performances and optmized
implementation can be improved later.

As such, I prefered to sick with a "dumb" and straight-forward
implementation that assumes the filesystem isn't changing, and relies on
existing high-level tools to do the job. For instance, it uses
**ZeroMQ** for TCP communication and more precisely the REP-REQ pattern
even if it's far from the most efficient to transfer files across a
network. [#1]_ It uses the Python standard library for its high-level
API (the :py:mod:`pathlib` module) to deal with path and files, as well
as its ability to serialize and de-serialize Python objects (see
:py:mod:`pickle` and :py:mod:`marshal` module) and thus simplifies
dealing with data sent across the network.

Implementing a FTP-like solution (that actually does more [#2]_) is a
lot of work for a single person. That's why I didn't focus on
performance. But at the end, it does the same job and with class, and
in 2018 with our powerful machines and fast lines, this is in most
scenarios **not** a problem; even if not tuned for performance it is
fast enough (its simplicity outweights). Also note that the
implementation can be improved over time to compress data and evoles
into a more optmized solution.

Upcoming improvements
---------------------
Initially I wrote the Remofile protocol and programming interface as
part of another software which needed file transfer features. And
because I prefer genericity, it slowly evolves into a project on its
own. Here are two important features which wasn't needed by the former
software but would enhance greatly Remofile.

* Resuming interupting file transfers
* Direct read/write file in Python code

Interupted file transfers are annoying when dealing with large files.
Even though implementing this feature isn't technically a challenge, it
does require to adapt the protocol. Also various decisions must be taken
such as where do the interupted file data resides (left in the remote
directory itself, or saved in a temporary directory?) and others. As
soon as I've got some time for that, I'll get down to it.

Another feature that could be useful is direct opening of remote file in
Python code. Basically, one would open a file using the  `open()`
function and reading and writing would happen transparently. Also, with
the new `pathlib` module, we can also imagine implementing a
`RemofilePath`.

See the :doc:`roadmap </roadmap>` document for more information.

.. [#0] Gitlab Runner, Buildbot, Jenkins and most CI services have custom code to transfer source code back and forth.
.. [#1] Usually, when it comes to transfering files, one would use a lower-level solution that directely deals with streams of bytes.
.. [#2] See its synchronization features and its ability to resume interupted file transfers.
