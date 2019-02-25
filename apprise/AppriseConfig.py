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

import six
import logging
from os import access
from os import R_OK
from os.path import isfile
from os.path import expanduser

from . import config
from . import ConfigBase
from .AppriseAsset import AppriseAsset

from .utils import GET_SCHEMA_RE
from .utils import parse_list
from .utils import is_exclusive_match

logger = logging.getLogger(__name__)


class AppriseConfig(object):
    """
    Our Apprise Configuration File Manager

        - Supports a list of URLs defined one after another (text format)
        - Supports a destinct YAML configuration format

    """

    # A default list of paths containing the location of potential
    # configuration files this object will be required to load.
    default_search_paths = (
        '~/.apprise',
        '~/.apprise.yml',
        '~/.config/apprise',
        '~/.config/apprise.yml',
    )

    def __init__(self, paths=None, asset=None):
        """
        Loads all of the paths specified (if any).

        The path can either be a single string identifying one explicit
        location, otherwise you can pass in a series of locations to scan
        via a list.

        If no path is specified then a default list is used.

        """

        # Initialize a server list of URLs
        self.configs = list()

        # Prepare our Asset Object
        self.asset = \
            asset if isinstance(asset, AppriseAsset) else AppriseAsset()

        # tidy our path list without obstructing the original one passed in
        if paths is None:

            # Load our default search paths; but only those that are found
            # locally
            paths = set([
                expanduser(p) for p in self.default_search_paths
                if isfile(expanduser(p)) and access(expanduser(p), R_OK)])

        # Store our paths
        self.add(paths)

        return

    def add(self, configs, asset=None, tag=None):
        """
        Adds one or more config URLs into our list.

        You can override the global asset if you wish by including it with the
        config(s) that you add.

        """

        # Initialize our return status
        return_status = True

        if isinstance(asset, AppriseAsset):
            # prepare default asset
            asset = self.asset

        if isinstance(configs, ConfigBase):
            # Go ahead and just add our configuration into our list
            self.configs.append(configs)
            return True

        if isinstance(configs, six.string_types):
            # Save our path
            configs = (configs, )

        elif not isinstance(configs, (tuple, set, list)):
            logging.error(
                "An invalid config path (type={}) was specified.".format(
                    type(configs)))

            return False

        # Iterate over our
        for url in configs:

            # Instantiate ourselves an object, this function throws or
            # returns None if it fails
            instance = AppriseConfig.instantiate(url, asset=asset, tag=tag)
            if not instance:
                return_status = False
                logging.error(
                    "Failed to load configuration url: {}".format(url),
                )
                continue

            # Add our initialized plugin to our server listings
            self.configs.extend(instance)

        # Return our status
        return return_status

    def services(self, tag=None):
        """
        Returns all of our services dynamically build based on parsed
        configuration.

        if the tag is specified (either a string or a set/list/tuple
        of strings), then only the notifications flagged with that
        tagged value are notified.  By default all added services
        are notified (tag=None)

        """
        services = list()

        # Build our tag setup
        #   - top level entries are treated as an 'or'
        #   - second level (or more) entries are treated as 'and'
        #
        #   examples:
        #     tag="tagA, tagB"                = tagA or tagB
        #     tag=['tagA', 'tagB']            = tagA or tagB
        #     tag=[('tagA', 'tagC'), 'tagB']  = (tagA and tagC) or tagB
        #     tag=[('tagB', 'tagC')]          = tagB and tagC

        for entry in self.configs:

            # Apply our tag matching based on our defined logic
            if tag is not None and not is_exclusive_match(tag, entry.tags):
                continue

            # Build ourselves a list of services dynamically and return the
            # as a list
            services.extend(entry.services())

        return services

    def parse(self, paths=None, encoding="utf-8"):
        """
        Takes one or more urls defined as either file:// https:// or http://
        and returns it's content as a unicode string for parsing.

        If the file:// has a ?encoding= entry, then it will over-ride the
        default value defined by this function.

        Processes all of the configuration files (if present) and
        returns a list of the argument sets

        If a path isn't specified, then use the default
        """

        result = list()

        # Load our listings
        if isinstance(paths, six.string_types):
            # Save our path
            paths = (paths, )

        elif not isinstance(paths, (tuple, set, list)):
            # we can't support defined set of paths
            # take an early return
            logger.warning(
                "An invalid config path (type={}) was specified."
                .format(type(paths)))
            return result

        # Return our constructed results
        return result

    @staticmethod
    def instantiate(url, asset=None, tag=None, suppress_exceptions=True):
        """
        Returns the instance of a instantiated configuration plugin based on
        the provided Server URL.  If the url fails to be parsed, then None
        is returned.

        """
        # Attempt to acquire the schema at the very least to allow our
        # configuration based urls.
        schema = GET_SCHEMA_RE.match(url)
        if schema is None:
            # Plan B is to assume we're dealing with a file
            schema = '{}://'.format(config.ConfigFile.protocol)
            url = '{}{}'.format(schema, ConfigBase.quote(url))

        else:
            # Ensure our schema is always in lower case
            schema = schema.group('schema').lower()

        # Some basic validation
        if schema not in config.SCHEMA_MAP:
            logger.error('Unsupported schema {}.'.format(schema))
            return None

        # Parse our url details of the server object as dictionary containing
        # all of the information parsed from our URL
        results = config.SCHEMA_MAP[schema].parse_url(url)

        if not results:
            # Failed to parse the server URL
            logger.error('Unparseable URL {}.'.format(url))
            return None

        # Build a list of tags to associate with the newly added notifications
        results['tag'] = set(parse_list(tag))

        # Prepare our Asset Object
        results['asset'] = \
            asset if isinstance(asset, AppriseAsset) else AppriseAsset()

        if suppress_exceptions:
            try:
                # Attempt to create an instance of our plugin using the parsed
                # URL information
                cfg_plugin = config.SCHEMA_MAP[results['schema']](**results)

            except Exception:
                # the arguments are invalid or can not be used.
                logger.error('Could not load URL: %s' % url)
                return None

        else:
            # Attempt to create an instance of our plugin using the parsed
            # URL information but don't wrap it in a try catch
            cfg_plugin = config.SCHEMA_MAP[results['schema']](**results)

        return cfg_plugin

    def clear(self):
        """
        Empties our configuration list

        """
        self.configs[:] = []
