#!/usr/bin/env python3

import signal
import sys
import logging
import logging.config
import pkg_resources

from pathlib import Path

from . import exiftool
from .ui import ui
from .log import log

logger = logging.getLogger(__name__)

class Sortingshop():
    """"""

    def __init__(self):
        """Initialise UI ... ."""
        self.ui = ui.UI()
        logger.info('initialised')

    def run(self):
        """Do"""
        # construct
        #self.ui.construct()
        # run
        #self.ui.run()
        self.ui.register_event('set_working_dir', self.on_set_working_dir)

        self.ui.register_command('n', 'short', self.load_next_picture,
                'next picture', 'display the next picture')
        self.ui.register_command('p', 'short', self.load_previous_picture,
                'previous picture', 'display the previous picture')
        self.ui.register_command('A', 'short', self.load_all_sources,
                'next sidecar', 'display tags from the next source')
        self.ui.register_command('N', 'short', self.load_next_source,
                'next sidecar', 'display tags from the next source')
        self.ui.register_command('P', 'short', self.load_previous_source,
                'previous sidecar', 'display tags from the previous source')

    def on_set_working_dir(self, params):
        pass

    def load_next_picture(self):
        pass

    def load_previous_picture(self):
        pass

    def load_all_sources(self):
        pass

    def load_next_source(self):
        pass

    def load_previous_source(self):
        pass

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
        signal.pause()

def signal_handler(signal_num, frame):
    """Log signal and call sys.exit(0).

    Positional arguments:
    signal_num -- unused
    frame -- unused
    """
    logger.error('recieved ' + signal.strsignal(signal_num))
    sys.exit(0)

if __name__ == '__main__':
    # catch SIGINT to let ExifTool exit gracefully
    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except Exception as error:
        logger.error(error, exc_info=True)
