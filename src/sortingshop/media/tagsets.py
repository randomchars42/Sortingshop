#!/usr/bin/env python3

import logging
from pathlib import Path

from .. import config

logger = logging.getLogger(__name__)

class Tagsets():
    """Represents a file containing abbreviations for sets of tags.

    Structure (plain text, UTF-8):
    ABBR TAG1,TAG2|TAG3
    [A-Za-z0-9-_] [\s*][A-Za-z0-9-_|](,[A-Za-z0-9-_|])*[\s*]
    ^            ^^    ^             ^                 ^
    |            ||    |             |                 whitespace gets trimmed
    |            ||    |             TAG2(|TAG3),...,TAGn
    |            ||    TAG1(|TAG2|TAG3) [hierarchical tags]
    |            |whitespace gets trimmed
    |            BLANK separates ABBREVIATION from TAGs
    ABBREVIATION (may contain anything but BLANK, keep it as simple as possible)

    The file may rest at the current working directory (file name: "tagsets") or
    a path prespecified in the configuration.
    """

    __file_name = 'tagsets'

    def __init__(self):
        """Initialisation."""
        self.__tagsets = {}

    def get_tagsets(self):
        """Return tagsets (dict: 'ABBR' => ['TAG1', ...])."""
        return self.__tagsets

    def get_tagset(self, abbreviation):
        """Return the list of tags for a given abbreviation or an empty list."""
        return self.__tagsets.get(abbreviation, [])

    def load_tagsets(self):
        """Try to load and parse the file.

        A file at the current working directory would take precedent over a file
        specified in the configuration.

        Raises
        - PermissionError in case of insufficient permissions
        """
        cfg = config.ConfigSingleton()
        tagsets = {}

        # try loading tagsets from those paths
        # load the file specified in the config first and then
        # let the local file add to / overwrite the other tagsets
        paths = [
            cfg.get('Paths', 'path_tagsets', default=''),
            '{}/{}'.format(
                cfg.get('Paths', 'working_dir', default=''),
                self.__file_name)
            ]

        for path in paths:
            print(path)
            if path == '':
                continue
            path = str(Path(path).expanduser())
            try:
                tagsets.update(self._load_file(path))
                logger.info('tagsets loaded from "{}"'.format(path))
            except FileNotFoundError:
                logger.info('could not open file "{}"'.format(path))

        self.__tagsets = tagsets
        return self.__tagsets

    def _load_file(self, path):
        """Load file from given path and return a dict.

        Returns a dict with the abbreviation as key and the associated tags as a
        list.

        Raises
        - FileNotFoundError if the file does not exist
        - PermissionError in case of insufficient permissions
        - ValueError in case of an empty path

        Positional arguments:
        path - string with the path of the file to load
        """
        if not isinstance(path, str) or path == '':
            logger.error('bad path ("{}")'.format(str(path)))
            raise ValueError

        path = Path(path)
        # simplify error handling by relabeling IsADirectoryError to
        # FileNotFoundError
        if path.is_dir():
            raise FileNotFoundError

        tagsets = {}

        lines = path.read_text().splitlines()
        for line in lines:
            # split abbreviation from tags
            try:
                abbr, tags = line.split(' ', 1)
                if abbr == '':
                    # line contained a BLANK at position 0
                    logger.error('Invalid line "{}" in file "{}"'.format(
                        line.rstrip(), str(path)))
                else:
                    # convert tags into list, strip \s and filter empty strings
                    # ("if tag")
                    tagsets[abbr] = [tag for tag in tags.split(',') if tag]
                    map(str.strip, tagsets[abbr])
                    logger.debug('loaded tagset: {} -> {}'.format(
                        abbr, ','.join(tagsets[abbr])))
            except ValueError:
                # line did not contain a BLANK
                logger.error('Invalid line "{}" in file "{}"'.format(
                    line.rstrip(), str(path)))
        return tagsets

    def get_default_tagset(self):
        """Return the tagset that should be applied to all pictures."""
        try:
            return self.__tagsets['ALL_PICTURES']
        except KeyError:
            return None

    def has_default_tagset(self):
        """Is there a tagset that should be applied to all pictures?"""
        return 'ALL_PICTURES' in self.__tagsets

