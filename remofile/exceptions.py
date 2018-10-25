# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

class RemofileException(Exception):
    """ Base exception for Remofile-related exceptions.

    Remofile-related exceptions excludes filesystem-related exceptions,
    except for :py:exc:`SourceNotFound` and :py:exc:`DestinationNotFound`
    which exist to simplify catching exceptions in some functions.
    """

class SourceNotFound(RemofileException):
    """ Source is not found.

    This exception is raised in upload/download/synchronize related
    functions to catch the numberous different exceptions that a bad
    source could raise.

    It's triggered if a source file doesn't exist, or if it isn't a file
    or a directory (according to the context).
    """

    pass

class DestinationNotFound(RemofileException):
    """ Destination is not found.

    This exception is raised in upload/download/synchronize related
    functions to catch the numberous different exceptions that a bad
    destination could raise.

    It's triggered if a destination directory doesn't exist or if it's
    not a directory.
    """

    pass

class BadRequestError(RemofileException):
    """ Bad request error occured.

    This exception is raised when the client sends a badly formatted
    request. For instance, it can occur when the server isn't ready to
    handle the request because it's not in a valid state.

    It's well explained in the protocol specifications
    :doc:`document </protocol-specifications>`.
    """

    def __init__(self):
        super(BadRequestError, self).__init__()

class CorruptedResponse(RemofileException):
    """ Corrupted response was received.

    This exception is raised when the client is unable to process
    the response returned by the server. The client stricly implements
    the protocol and if a response isn't expected or doesn't have the
    correct format, the response is said corrupted.

    A :py:attr:`message` describing how the response could not be
    processed is available in attribute.

    Examples of message.

        * Unable to extract response type from response
        * Invalid reason type in refuse response
        * Unable to extract message from error response

    The :py:attr:`error` attribute is the underlying exception message
    that was raised while processing the corrupted response.

    :ivar str message: Explicit message explaining how response is corrupted.
    :ivar str error: Underlying exception message.
    """

    def __init__(self, message, error):
        super(CorruptedResponse, self).__init__(message)

        self.message = message
        self.error = error

class UnexpectedError(RemofileException):
    """ Unexpected error occured.

    This exception is raised whenever the server couldn't fulfill the
    request because an unexpected error occured on the server side.

    It's well explained in the protocol specifications :doc:`document </protocol-specifications>`.

    :ivar str message: Underlying exception message that occured on the server.
    """

    def __init__(self, message):
        super(UnknownError, self).__init__(message)

        self.message = message

class FileNameError(OSError):
    """ File name is invalid.

    This exception is raised when the file name is incorrect as stated
    by the Remofile protcol.
    """

    pass
