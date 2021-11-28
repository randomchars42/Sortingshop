#!/usr/bin/env python3

import logging
from pathlib import Path

from . import metadatasource

logger = logging.getLogger(__name__)
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
            proposed = (parent_path.stem + '_' +
                    self.get_counter(value = False) +
                    parent_path.suffix + '.xmp')

        return super(Sidecar, self).rename(proposed)
