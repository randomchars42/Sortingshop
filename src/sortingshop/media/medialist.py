#!/usr/bin/env python3

import logging
from pathlib import Path
import os

from . import sidecar
from . import mediafile
from .. import config

logger = logging.getLogger(__name__)

class MediaList():
    """Represent a directory containing media.

    The directory and its 'deleted'-subdirectory are represented by a list of
    media items they contain. The list is ordered in such a way that a fresh
    scan will produce the same list no matter if items were moved between the
    main directory and the deleted subfolder.
    """

    def __init__(self, directory=''):
        """Initiate instance variables and parse the directory.

        Keyword arguments:
        directory -- the directory to parse
        """
        self._reset()
        if not directory == '':
            self.parse(directory)

    def _reset(self):
        """Reset all instance variables."""
        self.__mediafiles = []
        self.__missing_parents = []
        self.__no_access = []
        self.__duplicate_name = ''
        self.__current = 0

    def parse(self, directory):
        """Catch media files and sidecars in directory and directory/deleted.

        Expects sidecars to be named like their parent file + ".xmp", e.g.
        image.jpg.xmp for image.jpg.
        Some programmes (e.g. Darktable) may create multiple sidecars for one
        image, those should be named image_01.jpg.xmp, ..., image_99.jpg.xmp.

        Stores the name of media items which cannot be accessed or of sidecar
        files which do not have a parent along the way.

        Raises FileNotFoundError if the directory cannot be accessed.

        Positional arguments:
        directory -- path of the directory to scan (string or Path)
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(
                    'No such directory ("{}")'.format(directory))

        files = self._parse_directory(directory, reset=True)

        # parse the subdirectory "deleted" as well
        deleted_dir = directory.joinpath('deleted')

        if deleted_dir.exists():
            # do not erase all files from the main directory from the list
            files = self._parse_directory(deleted_dir, files=files, reset=False)

        self.__mediafiles = list(files.values())
        # sort by file name, regardless if file is in the 'deleted'-subfolder
        # this way the user can move file to and from the 'deleted'-
        # subfolder and retain ordering / the correct position of the index
        self.__mediafiles = sorted(self.__mediafiles,
                key=lambda mediafile: mediafile.get_name())

    def _parse_directory(self, directory, files=None, reset=False):
        """Scan the directory and catch media files and sidecars.

        Expects sidecars to be named like their parent file + ".xmp", e.g.
        image.jpg.xmp for image.jpg.
        Some programmes (e.g. Darktable) may create multiple sidecars for one
        image, those should be named image_01.jpg.xmp, ..., image_99.jpg.xmp.

        Stores the name of media items which cannot be accessed or of sidecar
        files which do not have a parent along the way.

        Raises FileNotFoundError if the directory cannot be accessed.

        Positional arguments:
        directory -- Path of the directory to scan

        Keyword arguments:
        files -- dictionary of files already present with the paths as keys
        reset -- reset the list before parsing? (boolean)
        """
        if reset:
            self._reset()
        if files is None:
            # cannot use files={} in function definition because of:
            # https://stackoverflow.com/a/959118/14979776
            files = {}
        logger.debug('parse "{}"'.format(directory))
        file_types = ['.jpg', '.jpeg', '.png', '.CR2', '.tif', '.tiff']

        # if a sidecar is encountered before it's parent (os.scandir returns an
        # arbitrary order) it's path is stored in this list so it is not added
        # twice
        implicit_parents = []

        with os.scandir(directory) as entries:
            for entry in entries:
                # filter hidden files and directories
                if entry.name.startswith('.') or not entry.is_file():
                    continue

                path = Path(entry.path)
                suffix = path.suffix.lower()

                # check if the file is writable
                if not self._check_file(path):
                    if suffix in file_types or suffix == '.xmp':
                        # remember that
                        self.__no_access.append(str(path))
                        continue

                # add sidecar
                if suffix == '.xmp':
                    logger.debug('create sidecar "{}"'.format(path))
                    scar = sidecar.Sidecar(path)
                    parent = scar.get_parent()
                    if parent is None:
                        # no parent exists
                        self.__missing_parents.append(str(path))
                        continue

                    # a parent exists in the given directory
                    try:
                        # check if mediafile with same name but different path
                        # exists
                        self._check_mediafile_name_exists(parent, files)

                        files[parent.name].add_sidecars([scar])
                    except KeyError:
                        # create a parent
                        files[parent.name] = mediafile.MediaFile(parent,
                                sidecars=[scar])
                        # remember it was created so it is not created twice
                        implicit_parents.append(parent.name)
                    continue
                # add mediafile
                elif suffix in file_types:
                    if path.name in implicit_parents:
                        # the file has already been added as a parent to a
                        # sidecar
                        implicit_parents.remove(path.name)
                        continue

                    try:
                        # check if mediafile with same name but different path
                        # exists
                        self._check_mediafile_name_exists(path, files)
                    except KeyError as error:
                        # the filename does not exist in the files dict
                        pass
                    logger.debug('create mediafile "{}"'.format(path))
                    files[path.name] = mediafile.MediaFile(path)
        return files

    def _check_mediafile_name_exists(self, mediafile, files):
        """Check if the name of a mediafile already exists in the given dict.

        This occurs if a media file with the same name is in the main directory
        and in the deleted-subdirectory

        Raises FileExistsError if a file with the same name exists in both
        directories.
        May raise a KeyError implicitly if the name does not exist so use within
        try ... except KeyError.

        Positional arguments:
        mediafile -- Path of the mediafile
        files -- Dict of MediaFiles with the name as keys
        """
        if not str(files[mediafile.name].get_path()) == str(mediafile):
            self.__duplicate_name = mediafile.name
            raise FileExistsError(
                    'File with same name at {} and {}'.format(
                        str(mediafile),
                        str(files[mediafile.name].get_path())))


    def _check_dir(self, path):
        """Checks if a directory can be accessed and is writable.

        Positional arguments:
        path -- Path to the directory
        """
        if not path.is_dir():
            return False
        return os.access(str(path), os.W_OK | os.R_OK | os.X_OK)

    def _check_file(self, path):
        """Checks if a file can be accessed and is writable.

        Positional arguments:
        path -- Path to the file
        """
        if not path.is_file():
            return False
        return os.access(str(path), os.W_OK | os.R_OK)

    def _ensure_dir_exists(self, path):
        """Checks if directory at Path is writeable or tries to create it.

        Positional arguments:
        path -- Path of the directory
        """
        if path.exists():
            return check_dir(path)
        elif self.check_dir(path.parent):
            os.mkdir(str(path))
            return check_dir(path)
        else:
            return False

    def get_missing_parents(self):
        """Return a list of sidecar-paths (string) with missing parents."""
        return self.__missing_parents

    def get_not_accessible_items(self):
        """Return a list of MetadataSources without proper access."""
        return self.__no_access

    def get_duplicate_name(self):
        """Return the file name that exists in working_dir and ./deleted."""
        return self.__duplicate_name

    def get_number_mediafiles(self):
        """Return the number of valid mediafiles."""
        return len(self.__mediafiles)

    def get_current_index(self):
        """Return the current index."""
        # add 1 for the user so it doesn't start with 0
        return self.__current + 1

    def get_mediafile_index(self, name):
        """Return the index of the mediafile.

        Raises FileNotFoundError if no file was found.

        Positional arguments:
        name -- the name to search for
        """
        for index, mediafile in enumerate(self.__mediafiles):
            if mediafile.get_name() == name:
                return index + 1
        raise FileNotFoundError('No such file in medialist')

    def get_mediafile(self, position):
        """Return the MediaFile at the requested position.

        Raises IndexError if no mediafiles are stored in the list.
        Raises FileNotFoundError if the requested file could not be found.

        Positional arguments:
        position -- string indicating the requested file ("first", "last",
            "next", "previous", "current", INDEX)
        """
        cfg = config.ConfigSingleton()

        if len(self.__mediafiles) == 0:
            raise IndexError

        index = self.__current

        if position == 'next':
            if self.__current >= len(self.__mediafiles) - 1:
                index = 0
            else:
                index += 1
        elif position == 'previous':
            if self.__current <= 0:
                if cfg.get('Renaming', 'rename_files', variable_type='boolean'):
                    # if auto-renaming files do not allow to move from last to
                    # first because it may mess up counters
                    index = 0
                else:
                    index = len(self.__mediafiles) -1
            else:
                index -= 1
        elif position == 'first':
            index = 0
        elif position == 'last':
            index = len(self.__mediafiles) - 1
        else:
            # if function is called directly by a command the argument will be a
            # list
            if isinstance(position, list):
                position = position[0]
            # interpret position as index
            try:
                # substract 1, see get_current_index
                position = int(position) - 1
                self.__mediafiles[position]
                index = position
            except (ValueError, IndexError):
                logger.error('Invalid medialist index requested ("{}")'.format(
                    str(position)))

        if not self.__mediafiles[index].exists():
            # file must have been removed by the user since building the list
            # remove it
            del self.__mediafiles[index]
            raise FileNotFoundError

        # free up some space be unloading the current mediaitem
        self.__mediafiles[self.__current].unload()

        self.__current = index

        try:
            self.__mediafiles[self.__current].load()
        except IndexError as error:
            pass

        return self.__mediafiles[self.__current]

    def get_mediafiles(self):
        """Return list of mediafiles."""
        return self.__mediafiles
