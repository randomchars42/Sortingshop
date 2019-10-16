#!/usr/bin/env python3

import logging
import logging.config
import pkg_resources

from pathlib import Path

from . import exiftool
from .ui import ui
from .log import log

logger = logging.getLogger(__name__)

class Sortingshop():
    def __init__(self):
        logger.info('init')
        et = exiftool.ExifToolSingleton()
        print(et.do('-ver')['text'])
        nui = ui.UI()

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

if __name__ == '__main__':
    main()
