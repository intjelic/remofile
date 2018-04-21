# Remofile

![](https://img.shields.io/pypi/v/remofile.svg) ![](https://img.shields.io/pypi/l/remofile.svg) ![](https://img.shields.io/pypi/pyversions/remofile.svg) [![Documentation Status](https://readthedocs.org/projects/remofile/badge/?version=latest)](http://remofile.readthedocs.io/en/latest/?badge=latest)

Remofile is a **protocol**, a **Python library** and a **command-line interface** to transfer files back and forth from/to a remote server. It's a **quick** and **easy-to-use** alternative to FTP and other transfer files tools.

It features:

- [x] All common file operations
- [x] Connectionless command-line interface
- [x] Bidirectional directory synchronization
- [x] Simple authentication based on tokens
- [x] Encrypted communication based on Curve
* [ ] Pick up interrupted transfered files
* [ ] Direct remote file reading and writing
* [x] Temporary and volatile server mode
- [x] Listening on a custom ZeroMQ socket

Because it's purposely designed to be simple, it doesn't support concurrent access, direct change of ownership and permissions, or any complex authentication system. However, it's secured and Remofile also is an excellent files **synchronization** tool.

## More information

**Website:** https://www.sonkun-dev.net/project/remofile

**Author:** Jonahan De Wachter (dewachter.jonathan[at]gmail[dot]com)

**Documentation:** https://remofile.readthedocs.io

**Repository:** https://github.com/sonkun/remofile
