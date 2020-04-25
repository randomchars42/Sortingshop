#!/usr/bin/env python3

import logging
from pathlib import Path

from . import mediaitem

logger = logging.getLogger(__name__)

class Sidecar(mediaitem.MediaItem):
    """Represent the relevant parts of a sidecar file (.xmp).

    The sidecar should be named like:
    - parent.SUFFIX.xmp or
    - parent_COUNTER.SUFFIX.xmp in case of > 1 sidecars per parent
    """

    def __init__(self, path):
        """Set the path (MediaItem.__init__) and try to find a parent.

        Positional arguments:
        path -- the path (string or Path)
        """
        super(Sidecar, self).__init__(path)

        # if a sidecar counter exists it will be set by find_parent
        self.__counter = None
        self.__parent_path = self.find_parent()

    def get_counter(self, value=True):
        """Return the the counter (string) or its value (int).

        Keyword arguments:
        value -- return the value? (boolean)
        """
        if value:
            return int(self.__counter)
        else:
            return self.__counter

    def get_parent(self):
        """Return the parent's Path."""
        return self.__parent_path

    def find_parent(self):
        """Return the Path to the sidecar's parent or None."""
        base = str(self.get_path().parent) + '/'

        # the sidecar should be named like:
        # 1) parent.SUFFIX.xmp or
        # 2) parent_COUNTER.SUFFIX.xmp in case of > 1 sidecars per parent

        # case 1
        # the stem of the sidecar is the name of the parent (Path().stem trims
        # to the first "." from the right, i.e. removes ".xmp")
        proposed = Path(base + self.get_path().stem)
        if proposed.exists():
            return proposed

        # case 2
        # the stem of the sidecar must contain a counter
        index_stem = proposed.stem.rfind('_')
        if index_stem < 1 :
            return None
        # everything before this counter should be the parent's stem
        stem = proposed.stem[0:index_stem]
        # so add the parent's suffix
        proposed = Path(base + stem + proposed.suffix)
        if not proposed.exists():
            return None

        self.__counter = proposed.stem[index_stem+1:]
        return proposed

    def rename(self, parent_path):
        """Rename the sidecar so that the names match again.

        Adds a counter of the same length if one existed before.

        Raises FileExistsError if the destination already exists.

        Positional arguments:
        parent_path: the path of the parent (Path / string)
        """
        parent_path = Path(parent_path)

        # the sidecar should be named like:
        # 1) parent.SUFFIX.xmp or
        # 2) parent_COUNTER.SUFFIX.xmp in case of > 1 sidecars per parent

        # case 1
        if self.__counter is None:
            proposed = Path(str(parent_path) + '.xmp')
        # case 2
        else:
            counter_length = len(self.__counter)
            proposed = Path(str(parent_path.parent) + '/' +
                    str(parent_path.stem) + '_' +
                    str(self.counter).zfill(counter_length) +
                    parent_path.suffix + '.xmp')

        if proposed.exists():
            raise FileExistsError(
                    'A file of that name already exists ("{}")'.format(
                        str(proposed)))
            return

        self.get_path().rename(proposed) if proposed.exists():
            self.set_path(proposed) return proposed
