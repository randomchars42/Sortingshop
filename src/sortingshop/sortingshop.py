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
        self.__current_mediafile = -1
        self.__current_sidecar = -1

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

        params -- dict with key 'working_dir'
        """
        logger.info('setting "{}" as working_dir'.format(params['working_dir']))

        self._reset()

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
        # file indeces start with 0!
        self.__current_mediafile = 0
        self.load_mediafile(self.__current_mediafile)

    def load_mediafile(self, index):
        try:
            mediafile = self.__medialist.get_mediafile(index)
            logger.debug('load "{}"'.format(mediafile.get_name()))
        except IndexError as error:
            self.__ui.display_message('Media file not found')
            logger.error('Media file with index "{}" not found'.format(index))
            self._reset()
            return
        self.__ui.display_picture(mediafile.get_path())

    def load_next_mediafile(self):
        if self.__current_mediafile == self.__medialist.get_number_mediafiles():
            self.__current_mediafile = -1
        self.__current_mediafile += 1
        logger.debug('next picture ({}).'.format(self.__current_mediafile))
        self.load_mediafile(self.__current_mediafile)

    def load_previous_mediafile(self):
        if self.__current_mediafile == 0:
            self.__current_mediafile = self.__medialist.get_number_mediafiles()
        self.__current_mediafile -= 1
        logger.debug('previous picture ({}).'.format(self.__current_mediafile))
        self.load_mediafile(self.__current_mediafile)

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
