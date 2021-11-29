#!/usr/bin/env python3

import logging
from pathlib import Path

from . import metadatasource
from .. import config

logger = logging.getLogger(__name__)

class Sidecar(metadatasource.MetadataSource):
    """Represent the relevant parts of a sidecar file (.xmp).

    The sidecar should be named like:
    - parent.SUFFIX.xmp or
    - parent_COUNTER.SUFFIX.xmp in case of > 1 sidecars per parent
    """

    def __init__(self, path):
        """Set the path (MetadataSource.__init__) and try to find a parent.

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
        self.__counter = proposed.stem[index_stem+1:]
        # so add the parent's suffix
        proposed = Path(base + stem + proposed.suffix)
        if not proposed.exists():
            return None

        return proposed

    def rename(self, parent_path):
        """Rename the sidecar so that the names match again.

        Adds a counter of the same length if one existed before.

        Raises
         - ValueError if parent_path is None
         - FileNotFoundError if parent_path does not exist
         - FileExistsError if a file with the proposed name already exists
         - PermissionError in case of insufficient permissions

        Positional arguments:
        parent_path: the path of the parent (Path / string)
        """
        if parent_path is None:
            logger.error('No parent_path given.')
            raise ValueError

        if not isinstance(parent_path, Path):
            parent_path = Path(parent_path)

        if not parent_path.exists():
            logger.error('No parent at "{}"'.format(str(parent_path)))
            raise FileNotFoundError

        # the sidecar should be named like:
        # 1) parent.SUFFIX.xmp or
        # 2) parent_COUNTER.SUFFIX.xmp in case of > 1 sidecars per parent

        # case 1
        if self.__counter is None:
            proposed = parent_path.name + '.xmp'
        # case 2
        else:
            cfg = config.ConfigSingleton()
            proposed = self._count_name_up(
                    cfg.get('Paths', 'working_dir', default=''),
                    parent_path.stem, parent_path.suffix + ".xmp",
                    cfg.get('Renaming', 'counter_length', default=3, variable_type="int"))

        return super(Sidecar, self).rename(proposed)
