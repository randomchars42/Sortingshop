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

    def __init__(self, ui):
        """Initialisation."""
        self.__tagsets = {}
        self.__ui = ui
        self.__ui.register_event('set_working_dir', self.load)
        self.__ui.register_event('update_tagsets', self.update_tagsets)
        self.__ui.register_event('save_tagsets', self.save_tagsets)

    def get_tagsets(self, origin='local'):
        """Return tagsets (dict: 'ABBR' => ['TAG1', ...])."""
        try:
            return self.__tagsets[origin]
        except KeyError:
            logger.error('invalid origin requested')
            return {}

    def get_tagset(self, abbreviation):
        """Return the list of tags for a given abbreviation or an empty list."""
        for origin in ['local', 'global']:
            try:
                return self.__tagsets[origin][abbreviation]
            except KeyError:
                continue
        return []

    def get_tagsets_text(self, origin):
        """Return the tagsets as parseable text."""
        text = ''
        for key, tagset in self.__tagsets[origin].items():
            text += "\n{} {}".format(key, ','.join(tagset))
        return text

    def load(self, params):
        """Try to load and parse the file.

        A file at the current working directory would take precedent over a file
        specified in the configuration.

        Positional arguments:
        params -- dict passed in by UI.fire_event()
        """
        logger.info('loading tagsets')
        # load tagsets
        cfg = config.ConfigSingleton()
        self.__tagsets = {'local':{}, 'global':{}}

        # try loading tagsets from those paths
        # load the file specified in the config first and then
        # let the local file add to / overwrite the other tagsets
        paths = {
                'global': cfg.get('Paths', 'path_tagsets', default=''),
                'local': '{}/{}'.format(params['working_dir'],
                    self.__file_name)
            }

        for origin, path in paths.items():
            if path == '':
                continue
            path = str(Path(path).expanduser())
            try:
                self.__tagsets[origin] = self._load_file(path, origin)
                logger.info('tagsets loaded from "{}"'.format(path))
            except FileNotFoundError:
                logger.info('could not open file "{}"'.format(path))
            except PermissionError:
                message = 'Insufficient rights to open tagsets file'
                self.__ui.display_message(message)
                logger.error(message)

        self.__ui.display_tagsets('local', self.get_tagsets('local'))
        self.__ui.display_tagsets('global', self.get_tagsets('global'))

    def _load_file(self, path, origin):
        """Load file from given path and return a dict.

        Returns a dict with the abbreviation as key and the associated tags as a
        list.

        Raises
        - FileNotFoundError if the file does not exist
        - PermissionError in case of insufficient permissions
        - ValueError in case of an empty path

        Positional arguments:
        path - string with the path of the file to load
        origin -- the origin of the text (filename or text)
        """
        if not isinstance(path, str) or path == '':
            logger.error('bad path ("{}")'.format(str(path)))
            raise ValueError

        path = Path(path)
        # simplify error handling by relabeling IsADirectoryError to
        # FileNotFoundError
        if path.is_dir():
            raise FileNotFoundError

        return self._parse_text(path.read_text(), origin)

    def _parse_text(self, text, origin=''):
        """Parse a text into a taglist.

        Positional arguments:
        text -- the text to parse

        Keyword arguments:
        origin -- the origin of the text (filename or text)
        """
        tagsets = {}

        lines = text.splitlines()
        for line in lines:
            # split abbreviation from tags
            try:
                abbr, tags = line.split(' ', 1)
                if abbr == '':
                    # line contained a BLANK at position 0
                    logger.error('Invalid line "{}" in file "{}"'.format(
                        line.rstrip(), origin))
                else:
                    # convert tags into list, strip \s and filter empty strings
                    # ("if tag")
                    tagsets[abbr] = [tag for tag in tags.split(',') if tag]
                    map(str.strip, tagsets[abbr])
                    logger.debug('loaded tagset: {} -> {}'.format(
                        abbr, ','.join(tagsets[abbr])))
            except ValueError:
                # line did not contain a BLANK
                logger.error('Invalid line "{}" in origin "{}"'.format(
                    line.rstrip(), origin))
        return tagsets

    def save_tagsets(self, params):
        """Save taglist from UI to file.

        Positional arguments:
        params -- dict passed in by UI.fire_event()
        """
        if not params['text']:
            logger.error('no text given')
            self.__ui.display_message('Could not save taglist.')
            return
        if not params['origin'] or not params['origin'] in ['local', 'global']:
            logger.error('no valid origin given ("{}")'.format(params[origin]))
            self.__ui.display_message('Could not save taglist.')
            return

        # update

        self.update_tagsets({'origin':params['origin'],'text':params['text']})

        # write

        cfg = config.ConfigSingleton()

        if params['origin'] == 'local':
            path = cfg.get('Paths', 'working_dir', default='')
            if path == '':
                logger.error('working_dir is empty')
                self.__ui.display_message('Could not save taglist.')
                return
            path = Path(path, 'tagsets')
        elif params['origin'] == 'global':
            path = Path(cfg.get('Paths', 'path_tagsets', default=''))
            if str(path) == '.':
                logger.error('path_tagsets is empty')
                self.__ui.display_message('Could not save taglist.')
                return

        try:
            path.expanduser().write_text(self.get_tagsets_text(params['origin']))
        except OSError as error:
            logger.error('could not write to "{}", because: {}'.format(
                str(path), error))
            self.__ui.display_message('Could not save taglist.')

    def update_tagsets(self, params):
        """Update taglist from UI.

        Positional arguments:
        params -- dict passed in by UI.fire_event()
        """
        if not params['text']:
            logger.error('no taglist given')
            self.__ui.display_message('Could not save taglist.')
            return
        if not params['origin'] or not params['origin'] in ['local', 'global']:
            logger.error('no valid origin given ("{}")'.format(params[origin]))
            self.__ui.display_message('Could not save taglist.')
            return

        self.__tagsets[params['origin']] = self._parse_text(params['text'],
                params['origin'])
        self.__ui.display_tagsets(params['origin'], self.get_tagsets(params['origin']))

    def get_default_tagset(self):
        """Return the tagset that should be applied to all pictures."""
        return self.get_tagset('ALL_PICTURES')
