#!/usr/bin/env python3

import logging
from pathlib import Path
from datetime import datetime

from .. import exiftool
from . import taglist

logger = logging.getLogger(__name__)

class MediaItem():
    """Base class for media files and sidecars.

    Communicates with ExifTool. MediaItems are identified with their paths.
    """

    def __init__(self, path, basepath):
        """Store the path of the file.

        Positional arguments:
        path -- path of the file (string / Path)
        basepath -- basepath (working directory; string / Path)
        """
        self._exiftool = exiftool.ExifToolSingleton()
        self.__path = Path(path)
        self.__basepath = Path(basepath)
        self.__taglist = taglist.TagList()
        self.__metadata = {}
        self._date = None

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
        """Is the item in the "deleted" subfolder?"""
        # subtract working directory from current path
        # yields either '.' or 'deleted'
        return str(self.__path.parent.relative_to(self.__basepath)) == 'deleted'

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

    def load(self):
        """Load metadata and determine create date."""
        # use "-s" to get names as used here: https://exiftool.org/TagNames/
        raw = self._exiftool.do(str(self.__path), '-s')['text']
        lines = raw.splitlines()

        for line in lines:
            key, value = line.split(sep=':', maxsplit=1)
            self.__metadata[key.strip()] = value.strip()

        # determine create date
        order = ['FileModifyDate', 'ModifyDate', 'CreateDate',
            'DateTimeOriginal']
        for key in order:
            date = self.__metadata.get(key, 'undefined')
            if not date == 'undefined':
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

#    def _increment_last_counter(self, name,
#            until = lambda new_name: True, parts = {}):
#        """Increment the value of the last counter until XXX.
#
#        See _get_name_parts for more detail.
#
#        Positional arguments:
#        name -- the name to use
#
#        Keyword arguments:
#        parts -- the parts as returned by _get_name_parts
#        """
#        if not len(parts) > 0:
#            parts = self.get_name_parts(name)
#
#        counter = 1
#
#        while counter < 10**parts['counter_length']:
#            proposed = self.set_last_counter(name, counter, parts)
#            if until(proposed):
#                return proposed
#            counter += 1
