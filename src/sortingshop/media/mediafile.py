#!/usr/bin/env python3

import logging
from pathlib import Path

from . import mediaitem
from . import sidecar

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
