#!/usr/bin/env python3

import signal
import sys
import logging
import logging.config
import pkg_resources

from pathlib import Path

from . import exiftool
from . import config
from .media import medialist
from .ui import wxpython
from .log import log

logger = logging.getLogger(__name__)

class Sortingshop():
    """"""

    def __init__(self):
        """Initialise UI ... ."""
        self.__ui = wxpython.WxPython()
        self._reset()
        logger.info('initialised')

    def _reset(self):
        """Reset instance variables related to media file handling."""
        self.__medialist = None

    def run(self):
        """Do"""
        # construct
        self.__ui.construct()

        # register events and commands
        self.__ui.register_event('set_working_dir', self.on_set_working_dir)

        self.__ui.register_command('n', 'short', self.load_next_mediafile,
                'next picture', 'display the next picture')
        self.__ui.register_command('p', 'short', self.load_previous_mediafile,
                'previous picture', 'display the previous picture')
        self.__ui.register_command('A', 'short', self.load_all_sources,
                'next sidecar', 'display tags from the next source')
        self.__ui.register_command('N', 'short', self.load_next_source,
                'next sidecar', 'display tags from the next source')
        self.__ui.register_command('P', 'short', self.load_previous_source,
                'previous sidecar', 'display tags from the previous source')
        self.__ui.register_command('t', 'long', self.toggle_tags,
                'toggle TAG1,TAG2', 'sets the tag if it is not present, else ' +
                'removes it')

        self.__ui.set_working_dir('/data/eike/Code/Test/Bilder')

        # needs to be the last call in this function
        self.__ui.run()

    def on_set_working_dir(self, params):
        """Load media files and config from the given directory.

        Positional arguments:
        params -- dict with key 'working_dir'
        """
        logger.info('setting "{}" as working_dir'.format(params['working_dir']))

        self._reset()

        cfg = config.ConfigSingleton()
        cfg.set('Paths', 'working_dir', params['working_dir'])

        self.__medialist = medialist.MediaList()
        try:
            self.__medialist.parse(params['working_dir'])
        except FileNotFoundError as error:
            # the directory does not exist
            self.__ui.display_message(
                    'Directory "{}" does not exist or is not accessible'.format(
                        params['working_dir']))
            logger.error(error, exc_info=True)
            self.__medialist = None
            return
        except FileExistsError as error:
            # the same media file name is used in working_dir and 
            # working_dir/deleted
            self.__ui.display_message(
                    'File "{}" exists in {} and {}/deleted'.format(
                        self.__medialist.get_duplicate_name(),
                        params['working_dir'], params['working_dir']))
            logger.error(error, exc_info=True)
            self.__medialist = None
            return
        self.load_mediafile('first')

    def load_mediafile(self, position):
        """ Load a mediafile and check if it has been removed since startup.

        After set_working_dir the working directory is scanned and a list is
        built. If the user (re)moves the files from that directory the change
        will not be automagically detected so this function checks if the
        requested file (first, last, next, previous, current) is available.

        Positional arguments:
        position -- string indicating the requested file ("first", "last",
            "next", "previous", "current")
        """
        media_file_found = False
        abort = False
        files_not_found = 0

        # - try to load the file
        # - if no file is found try again (the next / previous / new first /
        #   new last)
        # - if "current" is requested or no file remains in the list display a
        #   default image
        while media_file_found is False and abort is False:
            try:
                mediafile = self.__medialist.get_mediafile(position)
                logger.debug('load "{}"'.format(mediafile.get_name()))
            except FileNotFoundError as error:
                logger.error('{} media file not found'.format(position))
                if position == 'current':
                    self.__ui.display_message('Current media file not found ' + 
                        'anymore. Did you just remove it?')
                    # leave loop display default and continue...
                    abort = True
                    pass
                # count files
                files_not_found += 1
                pass
            except IndexError as error:
                self.__ui.display_message('No media files found.')
                logger.error('media list empty')
                abort = True
                pass
            else:
                media_file_found = True
        if not media_file_found:
            # no "current" mediafile or list is empty
            self.__ui.display_picture(None)
            return
        elif files_not_found > 0:
            self.__ui.display_message('{} file(s) not found anymore.'.format(
                str(files_not_found)))

        mediafile.prepare()
        self.__ui.display_picture(mediafile)

        self.__ui.display_metadata(mediafile.get_metadata())
        #self.__ui.display_tags(mediafile.get_standard_sidecar().get_taglist())

    def load_next_mediafile(self):
        logger.debug('next picture')
        self.load_mediafile('next')

    def load_previous_mediafile(self):
        logger.debug('previous picture')
        self.load_mediafile('previous')

    def load_source(self, index):
        logger.info('blah')

    def load_all_sources(self):
        logger.info('all sources')

    def load_next_source(self):
        logger.info('next source')

    def load_previous_source(self):
        logger.info('previous source')

    def toggle_tags(self, tags):
        logger.info('toggle tags')

def main():
    """Run the application.

    Configure logging and set correct ExifTool executable (packaged if it exists
    or system).

    Raises FileNotFoundError if no ExifTool executable could be detected.
    """
    logging.config.dictConfig(log.config)

    if pkg_resources.resource_exists(__name__, 'exiftool-src/exiftool'):
        executable=[
                pkg_resources.resource_filename(__name__, 'exiftool-src') +
                '/exiftool']
    elif Path('/usr/bin/exiftool').exists():
        executable=['/usr/bin/exiftool']
        logger.warning('No ExifTool executable detected at ' +
                '"src/sortingshop/exiftool-src/exiftool".')
    else:
        raise FileNotFoundError('No ExifTool executable detected.')

    with exiftool.ExifToolSingleton(executable=executable):
        sosho = Sortingshop()
        sosho.run()

def signal_handler(signal_num, frame):
    """Log signal and call sys.exit(0).

    Positional arguments:
    signal_num -- unused
    frame -- unused
    """
    logger.error('recieved signal ' + str(signal_num))
    sys.exit(0)

if __name__ == '__main__':
    # catch SIGINT to let ExifTool exit gracefully
    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except Exception as error:
        logger.error(error, exc_info=True)
