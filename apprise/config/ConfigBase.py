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
import six
import logging

from .. import plugins
from ..URLBase import URLBase
from ..utils import GET_SCHEMA_RE
from ..common import ConfigFormat
from ..common import CONFIG_FORMATS

logger = logging.getLogger(__name__)


class ConfigBase(object):
    """
    This is the base class for all supported configuration sources
    """

    # The Default Encoding to use if not otherwise detected
    encoding = 'utf-8'

    # The default expected configuration format unless otherwise
    # detected by the sub-modules
    default_config_format = ConfigFormat.TEXT

    # Don't read any more of this amount of data into memory as there is no
    # reason we should be reading in more. This is more of a safe guard then
    # anything else. 128KB (131072B)
    max_buffer_size = 131072

    # Logging
    logger = logging.getLogger(__name__)

    def __init__(self, **kwargs):
        """
        Initialize some general logging and common server arguments that will
        keep things consistent when working with the configurations that
        inherit this class.

        """

        super(ConfigBase, self).__init__(**kwargs)

        if 'encoding' in kwargs:
            # Store the encoding
            self.encoding = kwargs.get('encoding')

        if 'format' in kwargs:
            # Store the enforced config format
            self.config_format = kwargs.get('format').lower()

            if self.config_format not in CONFIG_FORMATS:
                # Simple error checking
                err = 'An invalid config format ({}) was specified.'.format(
                    self.config_format)
                self.logger.warning(err)
                raise TypeError(err)

        return

    def services(self, **kwargs):
        """
        Performs reads loaded configuration and returns all of the services
        that could be parsed and loaded.

        """

        # Our response object
        response = list()

        # read() causes the child class to do whatever it takes for the
        # config plugin to load the data source and return unparsed content
        # None is returned if there was an error or simply no data
        content = self.read(**kwargs)
        if not isinstance(content, six.string_types):
            # Nothing more to do
            return response

        # Our Configuration format uses a default if one wasn't one detected
        # or enfored.
        config_format = \
            self.default_config_format \
            if self.config_format is None else self.config_format

        # Dynamically load our parse_ function based on our config format
        fn = getattr(ConfigBase, 'config_parse_{}'.format(config_format))

        # Execute our config parse function
        result = fn(content)

        # Append our result set to our list
        if isinstance(result, list):
            response.extend(result)

        return response

    def read(self):
        """
        Iterate through all of our loaded configuration URLs and
        retrieve any notification plugins that we can.

        """
        raise NotImplementedError(
            "read() is not implimented by the child class.")

    @staticmethod
    def parse_url(url, verify_host=True):
        """Parses the URL and returns it broken apart into a dictionary.

        This is very specific and customized for Apprise.


        Args:
            url (str): The URL you want to fully parse.
            verify_host (:obj:`bool`, optional): a flag kept with the parsed
                 URL which some child classes will later use to verify SSL
                 keys (if SSL transactions take place).  Unless under very
                 specific circumstances, it is strongly recomended that
                 you leave this default value set to True.

        Returns:
            A dictionary is returned containing the URL fully parsed if
            successful, otherwise None is returned.
        """
        results = URLBase.parse_url(url, verify_host=verify_host)

        if not results:
            # We're done; we failed to parse our url
            return results

        # Allow overriding the default config format
        if 'format' in results['qsd']:
            results['format'] = results['qsd'].get('format')
            if results['format'] not in CONFIG_FORMATS:
                URLBase.logger.warning(
                    'Unsupported format specified {}'.format(
                        results['format']))
                del results['format']

        # Defines the encoding of the payload
        if 'encoding' in results['qsd']:
            results['encoding'] = results['qsd'].get('encoding')

        return results

    @staticmethod
    def config_parse_text(content):
        """
        Parse the specified content as though it were a simple text file only
        containing a list of URLs. Return a list of loaded notification plugins

        """
        # For logging, track the line number
        line = 0

        response = list()

        # Compile for speed on first pass though
        line_is_comment_re = re.compile(r'^\s*[;#].*$', re.I)

        content = re.split(r'\r*\n', content)

        for url in content:
            # Increment our line count
            line += 1

            if line_is_comment_re.match(url):
                # Ignore commented lines
                continue

            # swap hash (#) tag values with their html version
            _url = url.replace('/#', '/%23')

            # Attempt to acquire the schema at the very least to allow our
            # plugins to determine if they can make a better
            # interpretation of a URL geared for them
            schema = GET_SCHEMA_RE.match(_url)
            if schema is None:
                logger.warning(
                    'Unparseable schema:// found in URL '
                    '{} on line {}.'.format(url, line))
                continue

            # Ensure our schema is always in lower case
            schema = schema.group('schema').lower()

            # Some basic validation
            if schema not in plugins.SCHEMA_MAP:
                logger.warning(
                    'Unsupported schema {} on line {}.'.format(
                        schema, line))
                continue

            # Parse our url details of the server object as dictionary
            # containing all of the information parsed from our URL
            results = plugins.SCHEMA_MAP[schema].parse_url(_url)

            if not results:
                # Failed to parse the server URL
                logger.warning(
                    'Unparseable URL {} on line {}.'.format(url, line))
                continue

            try:
                # Attempt to create an instance of our plugin using the
                # parsed URL information
                plugin = plugins.SCHEMA_MAP[results['schema']](**results)

            except Exception:
                # the arguments are invalid or can not be used.
                logger.warning(
                    'Could not load URL {} on line {}.'.format(
                        url, line))
                return None

            # if we reach here, we successfully loaded our data
            response.append(plugin)

        # Return what was loaded
        return response

    @staticmethod
    def config_parse_yaml(content):
        """
        Parse the specified content as though it were a YAML file. Return a
        list of the loaded notification plugins.
        """
        response = list()

        # TODO

        return response
