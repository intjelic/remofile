# Remofile - Embeddable alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, March 2018

import shortuuid

def generate_token():
    return shortuuid.uuid()
