#!/usr/bin/env python3

import logging
import logging.config

from . import exiftool
from .ui import ui
from .log import log

logger = logging.getLogger(__name__)

class Sortingshop():
    def __init__(self):
        logger.info('init')
        nui = ui.UI()

def main():
    logging.config.dictConfig(log.config)

    with exiftool.ExifToolSingleton():
        sosho = Sortingshop()

if __name__ == '__main__':
    main()
