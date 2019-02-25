# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Chris Caron <lead2gold@gmail.com>
# All rights reserved.
#
# This code is licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions :
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import re
from os.path import getsize
from os.path import expanduser
from .ConfigBase import ConfigBase
from ..common import ConfigFormat


class NotifyFile(ConfigBase):
    """
    A wrapper for File based configuration sources
    """

    # The default descriptive name associated with the Notification
    service_name = 'Local File'

    # The default protocol
    protocol = 'file'

    def __init__(self, path, **kwargs):
        """
        Initialize File Object

        headers can be a dictionary of key/value pairs that you want to
        additionally include as part of the server headers to post with

        """
        super(NotifyFile, self).__init__(**kwargs)

        # Store file path
        self.path = expanduser(path)

        return

    def url(self):
        """
        Returns the URL built dynamically based on specified arguments.
        """

        # Define any arguments set
        args = {
            'encoding': self.encoding,
        }

        return 'file://{path}?{args}'.format(
            path=self.quote(self.path),
            args=self.urlencode(args),
        )

    def read(self, **kwargs):
        """
        Perform retrieval of the configuration based on the specified request
        """

        response = None

        try:
            if self.max_buffer_size > 0 and \
                    getsize(self.path) > self.max_buffer_size:

                # Content exceeds maximum buffer size
                self.logger.error(
                    'File size exceeds maximum allowable buffer length'
                    ' ({}KB).'.format(int(self.max_buffer_size / 1024)))
                return None

        except OSError:
            # getsize() can throw this acception if the file is missing
            # and or simply isn't accessible
            self.logger.error(
                'File is not accessible: {}'.format(self.path))
            return None

        # Always call throttle before any server i/o is made
        self.throttle()

        try:
            with open(self.path, "rt", encoding=self.encoding,
                      errors='strict') as f:
                # Store our content for parsing
                response = f.read()

        except ValueError:
            # A result of our strict encoding check; if we receive this
            # then the file we're opening is not something we can
            # understand the encoding of..

            self.logger.error(
                'File not using expected encoding ({}) : {}'.format(
                    self.encoding, self.path))
            return None

        except (IOError, OSError):
            # IOError is present for backwards compatibility with Python
            # versions older then 3.3.  >= 3.3 throw OSError now.

            # Could not open and/or read the file; this is not a problem since
            # we scan a lot of default paths.
            self.logger.debug(
                'File can not be opened for read: {}'.format(self.path))
            return None

        # Detect config format based on file extension if it isn't already
        # enforced
        if self.config_format is None and \
                re.match(r'^.*\.ya?ml\s*$', self.path, re.I) is not None:

            # YAML Filename Detected
            self.default_config_format = ConfigFormat.YAML

        self.logger.debug('Read Config File: %s' % (self.path))

        # Return our response object
        return response
