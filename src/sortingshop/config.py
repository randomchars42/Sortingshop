#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import configparser
import pkg_resources

from . import singleton

logger = logging.getLogger(__name__)

class Config():
    """Representation of the configuration.

    Configuration can be set in three different ways:
    * APPLICATION_PATH/settings/config.ini (application's defaults)
    * XDG_CONFIG_HOME/sortingshop/config.ini or ~/.config/sortingshop/config.ini
    * script params
    Where the latter configurations override the former configurations.
    """

    def __init__(self, flags={}):
        """Initialise variables and load config from file(s).
        """
        self._reset()
        config = configparser.ConfigParser(interpolation=None)
        # load from APPLICATION_PATH/settings/config.ini
        path = Path(pkg_resources.resource_filename(__name__,
            'settings/config.ini'))
        self._load_config(config, path)
        # load from XDG_CONFIG_HOME/sortingshop/config.ini if defined else from
        # ~/.config/sortingshop
        config_home = os.getenv('XDG_CONFIG_HOME')
        if not config_home:
            config_home = Path.home() / '.config'
        path = config_home.resolve()
        path = path / 'sortingshop' / 'config.ini'
        self.__config_stored = self._load_config(config, path)
        self.__config_effective = self.__config_stored

    def _reset(self):
        """Reset variables."""
        self.__config_stored = {}
        self.__config_effective = {}

    def _load_config(self, config, path):
        """Load config from file.

        Positional arguments:
        config -- configparser.ConfigParser()
        path -- Path to load config from
        """
        try:
            with open(path, 'r') as configfile:
                config.read_file(configfile)
        except FileNotFoundError:
            logger.debug('could not open config file at ' + str(path))
        else:
            logger.debug('loaded config from: ' + str(path))
        return config

    def get(self, *args, default=None, variable_type=None):
        """Return the specified configuration or default.

        Positional arguments:
        *args -- string(s), section / key to get

        Keyword arguments:
        default -- the default to return
        variable_type -- string, the type ("int", "float" or "boolean")
        """
        if variable_type == 'int':
            return self.__config_effective.getint(*args, fallback=default)
        elif variable_type == 'float':
            return self.__config_effective.getfloat(*args, fallback=default)
        elif variable_type == 'boolean':
            return self.__config_effective.getboolean(*args, fallback=default)
        else:
            return self.__config_effective.get(*args, fallback=default)

    def set(self, section, field, value):
        """Set a config value manually.

        Positional arguments:
        section -- string the section
        field -- string the key
        value -- string the value to set
        """
        try:
            self.__config_effective[section][field] = value
        except KeyError:
            logger.debug('could not set config value for "'+ str(section) +
                '.' + str(field) + '" to "' + value + '"')

class ConfigSingleton(Config, metaclass=singleton.Singleton):
    pass
