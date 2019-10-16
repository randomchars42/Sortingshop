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

    def run(self):
        """Do"""
        logger.info('running')

def main():
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
        signal.pause()

def signal_handler(signal, frame):
    """Call sys.exit(0).
    
    Used to catch SIGINT to let ExifTool shutdown gracefully.

    Positional arguments:
    signal -- unused
    frame -- unused
    """
    logger.error('recieved SIGINT')
    sys.exit(0)

if __name__ == '__main__':
    # catch SIGINT to let ExifTool exit gracefully
    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except Exception as e:
        logger.error(e, exc_info=True)
