#!/usr/bin/env python3

import logging
from pathlib import Path
from datetime import datetime

from .. import exiftool
from .. import config
from . import taglist

logger = logging.getLogger(__name__)

class MediaItem():
    """Base class for media files and sidecars.

    Communicates with ExifTool. MediaItems are identified with their paths.
    """

    def __init__(self, path):
        """Store the path of the file.

        Positional arguments:
        path -- path of the file (string / Path)
        """
        self._exiftool = exiftool.ExifToolSingleton()
        self.__path = Path(path)
        self.__taglist = taglist.TagList()
        self.__metadata = {}
        self._date = None
        self._is_loaded = False

    def get_path(self):
        """Return the path as Path."""
        return self.__path

    def set_path(self, path):
        """Set the path.

        Positional arguments:
        path -- the path (string / Path)
        """
        self.__path = Path(path)

    def get_name(self):
        """Return the filename as string."""
        return self.__path.name

    def _get_name_parts(self, name):
        """Return the different parts of the item's name.

        The item's name should be constructed like:
                        mediafile_001_01.jpg.xmp
                                      ^ ^
        Return values:                | index_suffix
                                      index_counter
                        stem: "mediafile_001_"
                        counter: "01"
                        counter_length: 2
                        suffix: ".jpg.xmp"

        Raises ValueError if parts of the name could not be detected.

        Positional arguments:
        name -- the name to use
        """
        index_stem = name.rfind('_') + 1
        if index_stem == 0:
            raise ValueError('Cannot find counter: no "_" in "' + name + '"')
        stem = name[0:index_stem]

        index_suffix = name.find('.')
        if index_suffix == -1:
            raise ValueError('Cannot find suffix: no "." in "' + name + '"')
        suffix = name[index_suffix:]

        counter_string = name[index_stem:index_suffix]
        counter_length = len(counter_string)
        if counter_length < 1:
            # special case: filename is STEM_.SUFFIX
            raise ValueError('Cannot find counter in "' + name + '"')
        return {
                'index_stem' : index_stem,
                'stem': stem,
                'index_suffix': index_suffix,
                'suffix': suffix,
                'counter': counter_string,
                'counter_length': counter_length}

    def _get_before_last_counter(self, name, parts = {}):
        """Return the part before the last counter.

        See _get_name_parts for more detail.

        Positional arguments:
        name -- the name to use

        Keyword arguments:
        parts -- the parts as returned by _get_name_parts
        """
        if not len(parts) > 0:
            parts = self.get_name_parts(name)
        return parts['stem']

    def _get_last_counter_value(self, name, parts = {}):
        """Return the value of the last counter as integer.

        See _get_name_parts for more detail.

        Positional arguments:
        name -- the name to use

        Keyword arguments:
        parts -- the parts as returned by _get_name_parts
        """
        if not len(parts) > 0:
            parts = self.get_name_parts(name)
        return int(parts['counter'])

    def _set_last_counter(self, name, counter, parts = {}):
        """Change the value of the last counter to the given number.

        See _get_name_parts for more detail.

        Raises ValueError if the counter is to large, e.g., the counter of the
        original name contains 2 digits but a 3-digit number is given.

        Positional arguments:
        name -- the name to use
        counter -- the value to set the counter to

        Keyword arguments:
        parts -- the parts as returned by _get_name_parts
        """
        if not len(parts) > 0:
            parts = self.get_name_parts(name)
        if not counter < 10**parts['counter_length']:
            raise ValueError('Counter too high')
        counter_string = str(counter).zfill(parts['counter_length'])
        return parts['stem'] + counter_string + parts['suffix']

    def is_deleted(self):
        """Is the item in the "deleted" subfolder?

        Raises ValueError if working_dir is not set in the configuration.
        """
        # subtract working directory from current path
        # yields either '.' or 'deleted'
        cfg = config.ConfigSingleton()
        basepath = cfg.get('Paths', 'working_dir', default=None)
        if basepath is None:
            raise ValueError
        return str(self.__path.parent.relative_to(basepath)) == 'deleted'

    def exists(self):
        """Check if the item has been removed after this object has been built.

        Checks if a file at the path exists and returns a boolean.
        """
        return self.__path.is_file()

    def unload(self):
        """Unload metadata."""
        self.__taglist = taglist.TagList()
        self.__metadata = {}
        self._date = None
        self._is_loaded = None

    def load(self):
        """Load metadata and determine create date."""
        # use "-s" to get names as used here: https://exiftool.org/TagNames/
        raw = self._exiftool.do(str(self.__path), '-n', '-s')['text']
        lines = raw.splitlines()

        # convert text lines into dict
        for line in lines:
            key, value = line.split(sep=':', maxsplit=1)
            self.__metadata[key.strip()] = value.strip()

        # determine create date
        order = ['FileModifyDate', 'ModifyDate', 'CreateDate',
            'DateTimeOriginal']
        for key in order:
            date = self.__metadata.get(key, None)
            if not date is None:
                # python's strptime / strftime expects time zone data like this:
                # +HHMM whereas exiftool may print it like +HH:MM
                # 2020:04:23 20:53:00+01:00
                if len(date) == 25:
                    date = date[:22] + date[23:]
                elif len(date) == 19:
                    date += '+0000'
                self._date = datetime.strptime(date, '%Y:%m:%d %H:%M:%S%z')
        if self._date is None:
            raise IndexError

        # load tags
        cfg = config.ConfigSingleton()
        tag_field = cfg.get('Metadata', 'field_tags', default=None)
        if tag_field is None:
            raise ValueError

        tags = self.get_metadata(keyword=tag_field, default='').split(', ')
        self.__taglist.load_tags(tags)

        self._is_loaded = True

    def is_loaded(self):
        return self._is_loaded

    def get_metadata(self, keyword=None, default='undefined'):
        """ Return all metadata or just a specific variable.

        Names are defined here: https://exiftool.org/TagNames/

        Keyword arguments:
        keyword -- string, if other than None try to return specific metadata
        default -- string, if keyword is not found return this string
        """
        if keyword is None:
            return self.__metadata
        else:
            return self.__metadata.get(keyword, default)

    def get_taglist(self):
        """Return the taglist."""
        return self.__taglist

    def rename(self, name=None):
        """Rename the file and return the new Path.

        Raises
         - ValueError if name is None
         - FileExistsError if a file with the proposed name already exists

        Keyword arguments:
        name -- string, the name to rename the file to
        """
        if name is None:
            raise ValueError
        target = Path(name)

        if target.exists():
            raise FileExistsError

        self.__path = self.__path.rename(target)

        return self.__path
