#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import configparser

from . import singleton

path_app = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)

class Config():
    """Representation of the configuration.

    Configuration can be set in three different ways:
    * APPLICATION_PATH/settings/config.ini (application's defaults)
    * XDG_CONFIG_HOME/sortingshop/config.ini or ~/.config/sortingshop/config.ini
    * script params
    Where the latter configurations override the former configurations.
    """

    def __init__(self, flags = {}):
        """Initialise variables and load config from file(s).
        """
        self._reset()
        config = configparser.ConfigParser()
        # load from APPLICATION_PATH/settings/config.ini
        path = path_app / Path('settings/config.ini')
        self._load_config(config, path)
        # load from XDG_CONFIG_HOME/sortingshop/config.ini if defined else from
        # ~/.config/sortingshop
        path = Path(os.getenv('XDG_CONFIG_HOME') or '~/.config').resolve()
        path = path / 'sortingshop' / 'config.ini'
        self._load_config(config, path)

    def _reset(self):
        self.__config_stored = {}
        self.__config_effective = {}

    def _load_config(self, config, path):
        try:
            with open(path, 'r') as configfile:
                config.read_file(configfile)
        except FileNotFoundError:
            logger.debug('could not open config file at ' + str(path))
        else:
            logger.debug('loaded config from: ' + str(path))
        return config

class ConfigSingleton(Config, metaclass=singleton.Singleton):
    pass
