# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

class RemofileException(Exception):
    """ Base exception for Remofile-related errors.

    Long description.
    """

class SourceNotFound(RemofileException):
    """ Brief description.

    Long description.
    """

    pass

class DestinationNotFound(RemofileException):
    """ Brief description.

    Long description.
    """

    pass

class InvalidFileName(RemofileException):
    """ Brief description.

    Long description.
    """

    pass

class FileAlreadyExists(RemofileException):
    """ Brief description.

    Long description.
    """

    pass

class UnexpectedError(RemofileException):
    """ This exception is raised because.

    Blabla.
    """

    def __init__(self, message):
        super(UnknownError, self).__init__(message)

        self.message = message

class BadRequestError(RemofileException):
    """ This exception is raised when the client sends a badly
    formatted request or when the server isn't ready to handle the
    request because it's not in a valid state.

    It's well explained in the protocol specifications :doc:`document </protocol-specifications>`.
    """

    def __init__(self):
        super(BadRequestError, self).__init__()


class UnknownError(RemofileException):
    """ This exception is raised when the server couldn't fulfill the
    request because an unexpected error occured on the server side.

    It's well explained in the protocol specifications :doc:`document </protocol-specifications>`.

    :ivar str message: Underlying exception message that occured on the server.
    """

    def __init__(self, message):
        super(UnknownError, self).__init__(message)

        self.message = message

class CorruptedResponse(RemofileException):
    """ This exception is raised when the client is unable to process
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
