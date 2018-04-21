# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

from enum import IntEnum

Request = IntEnum('Request', [
    'LIST_FILES',
    'CREATE_FILE',
    'MAKE_DIRECTORY',
    'UPLOAD_FILE',
    'SEND_CHUNK',
    'DOWNLOAD_FILE',
    'RECEIVE_CHUNK',
    'CANCEL_TRANSFER',
    'REMOVE_FILE'
])

Response = IntEnum('Response', [
    'ACCEPTED',
    'REFUSED',
    'ERROR'
])

Reason = IntEnum('Reason', [
    'FILES_LISTED',
    'FILE_CREATED',
    'DIRECTORY_CREATED',
    'INVALID_FILE_NAME',
    'FILE_NOT_FOUND',
    'FILE_ALREADY_EXISTS',
    'NOT_A_FILE',
    'NOT_A_DIRECTORY',
    'INCORRECT_FILE_SIZE',
    'INCORRECT_CHUNK_SIZE',
    'TRANSFER_ACCEPTED',
    'CHUNK_RECEIVED',
    'CHUNK_SENT',
    'TRANSFER_COMPLETED',
    'TRANSFER_CANCELLED',
    'BAD_REQUEST',
    'UNKNOWN_ERROR'
])

def make_list_files_request(directory):
    return (Request.LIST_FILES, directory)

def make_create_file_request(name, directory):
    return (Request.CREATE_FILE, name, directory)

def make_make_directory_request(name, directory):
    return (Request.MAKE_DIRECTORY, name, directory)

def make_upload_file_request(name, directory, file_size, chunk_size):
    return (Request.UPLOAD_FILE, name, directory, file_size, chunk_size)

def make_send_chunk_request(chunk_data):
    return (Request.SEND_CHUNK, chunk_data)

def make_receive_chunk_request():
    return (Request.RECEIVE_CHUNK,)

def make_cancel_transfer_request():
    return (Request.CANCEL_TRANSFER,)

def make_download_file_request(name, directory, chunk_size):
    return (Request.DOWNLOAD_FILE, name, directory, chunk_size)

def make_files_listed_response(files_list):
    return (Response.ACCEPTED, Reason.FILES_LISTED, files_list)

def make_file_created_response():
    return (Response.ACCEPTED, Reason.FILE_CREATED)

def make_directory_created_response():
    return (Response.ACCEPTED, Reason.DIRECTORY_CREATED)

def make_invalid_file_name_response():
    return (Response.REFUSED, Reason.INVALID_FILE_NAME)

def make_file_not_found_response():
    return (Response.REFUSED, Reason.FILE_NOT_FOUND)

def make_file_already_exists_response():
    return (Response.REFUSED, Reason.FILE_ALREADY_EXISTS)

def make_not_a_directory_response():
    return (Response.REFUSED, Reason.NOT_A_DIRECTORY)

def make_not_a_file_response():
    return (Response.REFUSED, Reason.NOT_A_FILE)

def make_transfer_accepted_response(file_size=None):
    if file_size:
        return (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED, file_size)
    else:
        return (Response.ACCEPTED, Reason.TRANSFER_ACCEPTED)

def make_chunk_received_response():
    return (Response.ACCEPTED, Reason.CHUNK_RECEIVED)

def make_chunk_sent_response(chunk_data):
    return (Response.ACCEPTED, Reason.CHUNK_SENT, chunk_data)

def make_transfer_completed_response(chunk_data=None):
    if chunk_data:
        return (Response.ACCEPTED, Reason.TRANSFER_COMPLETED, chunk_data)
    else:
        return (Response.ACCEPTED, Reason.TRANSFER_COMPLETED)

def make_transfer_cancelled_response():
    return (Response.ACCEPTED, Reason.TRANSFER_CANCELLED)

def make_incorrect_file_size_response():
    return (Response.REFUSED, Reason.INCORRECT_FILE_SIZE)

def make_incorrect_chunk_size_response():
    return (Response.REFUSED, Reason.INCORRECT_CHUNK_SIZE)

def make_bad_request_error():
    return (Response.ERROR, Reason.BAD_REQUEST)

def make_unknown_error_response(error_message):
    return (Response.ERROR, Reason.UNKNOWN_ERROR, error_message)
