#!/usr/bin/env python3

import logging
from pathlib import Path
import re

from . import mediaitem
from . import sidecar
from .. import config

logger = logging.getLogger(__name__)

class MediaFile(mediaitem.MediaItem):
    """"""

    def __init__(self, path, basepath, sidecars=[]):
        """Store the path (MediaItem.__init__) and create list of sidecars.

        Positional arguments:
        path -- the path of the file (string / Path)
        basepath -- the path of the working directory (string / Path)

        Keyword arguments:
        sidecars -- List of Sidecars
        """
        super(MediaFile, self).__init__(path, basepath)
        self.__sidecars = []
        self.add_sidecars(sidecars)

    def add_sidecars(self, sidecars=[]):
        """Add sidecars.

        Raises ValueError if one of the list items is not a sidecar.

        Keyword arguments:
        sidecars -- List of Sidecars
        """
        for scar in sidecars:
            if not isinstance(scar, sidecar.Sidecar):
                raise ValueError('not a sidecar ("{}")'.format(str(scar)))

        self.__sidecars += sidecars

    def load(self):
        """Load self (see MediaItem) and all sidecars."""
        super(MediaFile, self).load()
        for index in range(len(self.__sidecars)):
            self.__sidecars[index].load()

    def unload(self):
        """Unload self (see MediaItem) and all sidecars."""
        super(MediaFile, self).unload()
        for index in range(len(self.__sidecars)):
            self.__sidecars[index].unload()

    def is_named_correctly(self):
        """Checks if the file is named correctly.

        Because exiftool's syntax is too advanced the user is required to
        provide a matching regex. This regex may contain variables that can be
        interpreted by datetime.strftime().
        """
        cfg = config.ConfigSingleton()
        # load detect scheme from config and let strftime replace all variables
        regex = self._date.strftime(cfg.get('RENAMING', 'detect_scheme'))
        if not re.fullmatch(re.compile(regex), self.get_name()) is None:
            return True
        else:
            return False

    def rename(self, name=None):
        """Use exiftool to rename the file and return the new Path.

        Keyword arguments:
        name -- string, the name to rename the file to (ignored)
        """
        cfg = config.ConfigSingleton()
        commands = cfg.get('RENAMING', 'rename_command').strip().split()
        if len(commands) == '':
            logger.error('no rename_command in config')
            raise ValueError
        commands.append(str(self.get_path()))
        result = self._exiftool.do(*commands)

        path = self.get_path().parent / result['new_name']

        if result['new_name'] == '' or not path.is_file():
            logger.warning('could not rename file {}'.format(self.get_name()))
            raise FileNotFoundError
        logger.debug('set name of {} to {}'.format(self.get_name(),
            result['new_name']))

        self.set_path(path)

        for index in range(len(self.__sidecars)):
            self.__sidecars[index].rename(path)

        return path
