# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

invalid_characters = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

def is_file_name_valid(name):
    """ Brief description.

    Long description.

    :param name: Description.
    """

    for invalid_character in invalid_characters:
        if name.find(invalid_character) != -1:
            return False

    return True
