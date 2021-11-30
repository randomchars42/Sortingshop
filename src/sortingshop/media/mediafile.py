#!/usr/bin/env python3

import logging
from pathlib import Path
import re

from . import metadatasource
from . import sidecar
from .. import config

logger = logging.getLogger(__name__)

class MediaFile(metadatasource.MetadataSource):
    """"""

    def __init__(self, path, sidecars=[]):
        """Store the path (MetadataSource.__init__) and create list of sidecars.

        Positional arguments:
        path -- the path of the file (string / Path)

        Keyword arguments:
        sidecars -- List of Sidecars
        """
        super(MediaFile, self).__init__(path)
        self.__sidecars = []
        self.__sidecar_standard_index = None
        self.__source_index = None
        self.__current_source = None
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
            self.__sidecars.append(scar)
            if scar.get_name() == '{}.xmp'.format(self.get_name()):
                self.__sidecar_standard_index = len(self.__sidecars) - 1
                logger.debug('standard sidecar detected')

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

    def get_sidecar_at_index(self, index):
        """Return the sidecar at the given index.

        Raises IndexError if there is no sidecar with the given index.

        Positional Arguments:
        index -- integer index of the sidecar to retrieve
        """
        try:
            scar = self.__sidecars[index]
        except IndexError:
            logger.error('no sidecar at index {}'.format(index))
            raise IndexError

        return sidecar

    def get_source(self, position):
        """Return the MetadataSource at the requested position.

        Cycles through MetadataSources.

        MetadataSources could be:
          - the MediaFile itself (index -1)
          - any Sidecar (indices 0 to n-1)

        Raises FileNotFoundError if the requested sidecar file could not be
        found.
        Raises IndexError if not even the MediaFile (the caller) can be found
        anymore.

        Positional arguments:
        position -- string indicating the requested file ("first", "last",
            "next", "previous", "current", PATH)
        """
        cfg = config.ConfigSingleton()
        use_sidecar = cfg.get('Metadata', 'use_sidecar',
                variable_type='boolean', default=False)

        if self.__source_index is None:
            # start (index is None) with:
            # - Sidecar (config: use_sidecar = True) -> index: 0
            # - MediaFile -> index -1
            self.__source_index = 0 if use_sidecar else -1

        index = self.__source_index

        if position == 'next':
            if self.__source_index >= len(self.__sidecars) - 1:
                index = -1
            else:
                index += 1
        elif position == 'previous':
            if self.__source_index <= -1:
                index = len(self.__sidecars) -1
            else:
                index -= 1
        elif position == 'first':
            index = 0 if use_sidecar else -1
        elif position == 'last':
            index = len(self.__sidecars) - 1
        else:
            # if function is called directly by a command the argument will be a
            # list
            if isinstance(position, list):
                position = position[0]
            # interpret position as name (path)
            if position == self.get_name():
                index = -1
            else:
                for i, scar in enumerate(self.__sidecars):
                    index = i if scar.get_name() == position else index

        if index >= 0:
            source = self.__sidecars[index]
        else:
            source = self

        if not source.exists():
            # file must have been removed by the user since building the list
            # remove it
            if index >= 0:
                # remove non-existend sidecar
                del self.__sidecar[index]
                raise FileNotFoundError
            else:
                # not even the MediaFile exists anymore
                # the fake list (MediaFile + Sidecars) is "empty" so raise an
                # IndexError
                raise IndexError

        self.__source_index = index
        self.__current_source = source

        if self.__source_index >= 0:
            self.__current_source.load()

        return self.__current_source

    def get_primary_source(self):
        """Get the primary source, either Mediafile or Sidecar."""
        cfg = config.ConfigSingleton()
        use_sidecar = cfg.get('Metadata', 'use_sidecar',
                variable_type='boolean', default=False)
        if use_sidecar:
            return self.get_standard_sidecar()
        else:
            return self

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

    def prepare(self, tagsets=None):
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
        apply_default_tagset = cfg.get('Metadata', 'apply_default_tagset',
                variable_type='boolean', default=False)

        if soft_check:
            logger.debug('soft checking')
            if not rename_files or self.is_named_correctly():
                logger.debug('is named correctly')
                if not use_sidecar:
                    logger.info('{} already looks prepared'.format(
                        str(self.get_path())))
                    self.__is_prepared = True
                elif use_sidecar and self.has_standard_sidecar():
                    logger.debug('has a standard sidecar')
                    logger.info('{} already looks prepared'.format(
                        str(self.get_path())))
                    self.__is_prepared = True

        if not self.__is_prepared:
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

        # this can only happen if a sidecar has already been created in case
        # of use_sidecar
        if apply_default_tagset and not tagsets is None:
            logger.debug('applying default tags')
            default_tagset = tagset.get_default_tagset()
            if len(default_tagset) > 0:
                self.get_primary_source().toggle_tags(default_tagset,
                        tagsets=tagsets, force="in")
        self.__is_prepared = True

    def load(self):
        """Load self (see MetadataSource) and all sidecars."""
        super(MediaFile, self).load()
        for index in range(len(self.__sidecars)):
            self.__sidecars[index].load()
        self.__source_index = None

    def unload(self):
        """Unload self (see MetadataSource) and all sidecars."""
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
        name = Path(self._exiftool.do(*commands)['new_name'])

        # picks the right path whether in working_dir or "deleted"
        path = self.get_path().parent

        if name == '' or not name.is_file():
            logger.warning('could not rename file {}'.format(self.get_name()))
            raise FileNotFoundError

        working_dir = cfg.get('Paths', 'working_dir', default = '')
        if working_dir == '':
            raise FileNotFoundError

        logger.debug('set name of {} to {}'.format(self.get_name(), name))

        self.set_path(name)

        if Path(working_dir, name.name).exists() and Path(working_dir, 'deleted', name.name).exists():
            # if there are now two files with the same name, this one in a
            # pre-existing 'deleted' directory the other not (or vice-versa)
            # we need to count this one's name up
            logger.debug('duplicate filename after renaming ("{}")'.format(
                name))

            # the counter length
            length = cfg.get('Renaming', 'counter_length', default = 3,
                    variable_type = 'int')
            # does the new name already incorporate a counter
            has_counter = cfg.get('Renaming', 'mediafile_name_has_counter',
                    default = False)
            # if there's a counter in the stem remove it
            stem = name.stem[:(length+1)*-1] if has_counter else name.stem
            # test if the name exists in both the "deleted" directory and
            # the working directory
            name = self._count_name_up(
                    cfg.get('Paths', 'working_dir', default=''),
                    stem, name.suffix, length)
            logger.debug('renaming "{}" to "{}"'.format(
                self.get_name(), name))
            super(MediaFile, self).move(path / name)

        for index in range(len(self.__sidecars)):
            self.__sidecars[index].rename(path / name)

        return self.get_path()

    def move(self, target):
        """Move the file and its sidecars.

        Positional arguments:
        target -- string or Path
        """
        super(MediaFile, self).move(target)
        for scar in self.__sidecars:
            scar.move(target)

    def get_sources(self):
        """Return a list of the filenames of all sources attached."""
        sources = [self.get_metadata().get('FileName')]
        for source in self.__sidecars:
            sources.append(source.get_metadata().get('FileName'))
        return sources
