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

    def __init__(self, path, sidecars=[]):
        """Store the path (MediaItem.__init__) and create list of sidecars.

        Positional arguments:
        path -- the path of the file (string / Path)

        Keyword arguments:
        sidecars -- List of Sidecars
        """
        super(MediaFile, self).__init__(path)
        self.__sidecars = []
        self.__sidecar_standard_index = None
        self.add_sidecars(sidecars)
        self.__is_prepared = False

    def add_sidecars(self, sidecars=[]):
        """Add sidecars.

        Raises ValueError if one of the list items is not a sidecar.

        Keyword arguments:
        sidecars -- List of Sidecars
        """
        logger.debug('adding sidecars to {}'.format(self.get_name()))
        for scar in sidecars:
            if not isinstance(scar, sidecar.Sidecar):
                raise ValueError('not a sidecar ("{}")'.format(str(scar)))
            logger.debug('adding {} as sidecar'.format(scar.get_name()))
            if scar.get_name() == '{}.xmp'.format(self.get_name()):
                logger.debug('standard sidecar detected')
                self.__sidecar_standard_index = len(self.__sidecars)
            self.__sidecars.append(scar)

    def has_standard_sidecar(self):
        """Returns True if a sidecar named NAME.EXTENSION.xmp exists."""
        if not self.__sidecar_standard_index is None:
            return True
        return False

    def get_standard_sidecar(self):
        """Returns the standard sidecar or None."""
        if not self.__sidecar_standard_index is None:
            return self.__sidecars[self.__sidecar_standard_index]
        return None

    def _unify_dates(self):
        """Write one date to all variables that represent the creation date.

        Use the first available:
        DateTimeOriginal > CreateDate > ModifyDate > FileModifyDate
        """
        result = self._exiftool.do(
                '-overwrite_original',
                '-AllDates<FileModifyDate',
                '-AllDates<ModifyDate',
                '-AllDates<CreateDate',
                '-AllDates<DateTimeOriginal',
                str(self.get_path()))

    def _create_standard_sidecar(self):
        """Create a standard sidecar using exiftool if it doesn't exist.

        Raises ValueError if mandatory_metadata is not set.
        Raises FileNotFoundError if creation of sidecar did not succeed.
        """
        cfg = config.ConfigSingleton()
        metadata = cfg.get('Metadata', 'mandatory_metadata').strip().split()
        if len(metadata) == '':
            logger.error('no mandatory tags in config')
            raise ValueError

        for index in range(len(metadata)):
            metadata[index] = '-{}'.format(metadata[index])

        path = str(self.get_path())
        sidecar_path = '{}.xmp'.format(path)

        if self.has_standard_sidecar():
            overwrite = '-overwrite_original'
        else:
            overwrite = ''

        self._exiftool.do(
                overwrite,
                '-tagsfromfile', path,
                *metadata,
                sidecar_path)
        if not Path(sidecar_path).is_file():
            raise FileNotFoundError
        if not self.has_standard_sidecar():
            self.add_sidecars([sidecar.Sidecar(sidecar_path)])

    def _remove_sidecar(self, index):
        """Removes the requested sidecar.

        Raises FileNotFoundError if no such sidecar exists.

        Positional arguments:
        index -- int, the index
        """
        try:
            scar = self.__sidecars[index]
        except IndexError:
            raise FileNotFoundError

        if not scar.exists():
            raise FileNotFoundError
        scar.get_path().unlink()
        del self.__sidecars[index]

    def _sidecar_to_mediafile(self, index):
        """Transfers metadata from the requested sidecar to the mediafile.

        Raises FileNotFoundError if no such sidecar exists.
        Raises ValueError if no mandatory metadata is specified in config.

        Positional arguments:
        index -- int, the index
        """
        try:
            scar = self.__sidecars[index]
        except IndexError:
            raise FileNotFoundError

        metadata = cfg.get('Metadata', 'mandatory_metadata').strip().split()
        if len(metadata) == '':
            logger.error('no mandatory metadata in config')
            raise ValueError

        for index in range(len(metadata)):
            metadata[index] = '-{}'.format(metadata[index])

        self._exiftool.do(
                '-tagsfromfile', str(scar.get_path()),
                *metadata,
                '-o', str(self.get_path()))

    def _prune(self):
        """Remove all specified metadata.

        Raises ValueError if no mandatory metadata is specified in config.
        """
        cfg = config.ConfigSingleton()
        metadata = cfg.get('Metadata', 'remove_metadata').strip().split()
        if len(metadata) == '':
            logger.error('no metadata to remove in config')
            raise ValueError

        for index in range(len(metadata)):
            metadata[index] = '-{}='.format(metadata[index])

        self._exiftool.do(
                '-overwrite_original',
                *metadata,
                '-m', str(self.get_path()))

    def prepare(self):
        """Central function to keep your mediafiles clean."""

        logger.debug('prepare {}'.format(self.get_name()))

        if not self.is_loaded():
            logger.error('could not prepare {} (not loaded)'.format(
                str(self.get_path())))
            return

        if self.__is_prepared:
            logger.debug('{} already looks prepared'.format(
                str(self.get_path())))
            return

        cfg = config.ConfigSingleton()
        use_sidecar = cfg.get('Metadata', 'use_sidecar',
                variable_type='boolean', default=False)
        rename_files = cfg.get('Renaming', 'rename_files',
                variable_type='boolean', default=False)
        prune_metadata = cfg.get('Metadata', 'prune_metadata',
                variable_type='boolean', default=False)
        soft_check = cfg.get('Metadata', 'soft_check',
                variable_type='boolean', default=False)

        if soft_check:
            logger.debug('soft checking')
            if not rename_files or self.is_named_correctly():
                logger.debug('is named correctly')
                if not use_sidecar or self.has_standard_sidecar():
                    logger.debug('has a standard sidecar')
                    logger.info('{} looks already prepared'.format(
                        str(self.get_path())))
                    self.__is_prepared = True
                    return

        self._unify_dates()

        if use_sidecar or prune_metadata:
            self._create_standard_sidecar()

        if prune_metadata:
            self._prune()

        if not use_sidecar and prune_metadata:
            self._sidecar_to_mediafile(self.__sidecar_standard_index)
            self._remove_sidecar(self.__sidecar_standard_index)

        # renaming enabled and file needs renaming
        if rename_files and not self.is_named_correctly():
            self.rename()
        self.unload()
        self.load()
        self.__is_prepared = True

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
        regex = self._date.strftime(cfg.get('Renaming', 'detect_scheme'))
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
        commands = cfg.get('Renaming', 'rename_command').strip().split()
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
