#!/usr/bin/env python3

import logging
import subprocess
import sys
import os
from pathlib import Path
import re

from . import singleton

path_app = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)

class ExifTool():
    """A Wrapper around ExifTool-CLI.

    Starts an instance of exiftool with stay_open = True, and creates a pipe in
    and out to communicate.

    Kudos to Sven Marnach https://stackoverflow.com/questions/10075115
    """

    def __init__(self, executable=['/usr/bin/exiftool'],
            config=path_app.joinpath('settings/exiftool_config.txt')):
        """Set path to the executables: perl and exiftool.

        Raises ValueError if `executable` is not a list.

        Keyword arguments:
        executable -- list of commands to call ExifTool executable
                      (default: ['/usr/bin/exiftool'])
        """
        if not isinstance(executable, list):
            raise ValueError('executable needs to be a list')
        self.executable = executable

        # on Windows the ready sign ends with "\r\n" instead of "\n"
        if sys.platform.startswith('win32'):
            self.sign_ready = "{ready}\r\n"
        else:
            self.sign_ready = "{ready}\n"

        self.config = str(config)

    def __enter__(self):
        """Start a process for ExifTool and let it stay open to communicate."""
        command = self.executable
        if not self.config == '':
            command  += ['-config', self.config]
        self.process = subprocess.Popen(command +  ['-stay_open', 'True',
                '-@', '-'],
            universal_newlines=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        logger.info('started ExifTool')
        return self

    def  __exit__(self, exc_type, exc_value, traceback):
        """Shutdown ExifTool."""
        self.process.stdin.write("-stay_open\nFalse\n")
        self.process.stdin.flush()
        self.process.stdin.close()
        self.process.stdout.close()
        logger.info('shut down ExifTool')

    def do(self, *args):
        """Pipe a command to ExifTool and read the answer.

        Positional arguments:
        *args -- at least one command as string, set an extra string for each
                 parameter for ExifTool.
        """
        action = "\n".join(args + ("-execute\n",))
        logger.debug('command: ' + ' '.join(args))
        self.process.stdin.write(action)
        self.process.stdin.flush()
        chunks = ''
        fd = self.process.stdout.fileno()
        while not chunks.endswith(self.sign_ready):
            chunks += os.read(fd, 4096).decode('utf-8')
        raw_output = chunks[:-len(self.sign_ready)].strip()
        return self.parse_result(raw_output)

    def do_for(self, for_in=[], *args):
        """Same as do but applies *args to all targets.

        Keyword arguments:
        for_in -- list of strings, for each string all other arguments will be
                  called

        Positional arguments:
        *args -- see do, but "#FOR#" will be replaced by each string in for_in
        """
        args = list(args)
        results = []
        i = 0
        for string in for_in:
            args_current = [item.replace('#FOR#', string) for item in args]
            results[i] = self.do(*args_current)
            i += 1
        return results

    def parse_result(self, raw):
        """Parse the raw result and return a list of processable results."""
        result = {}
        result['text'] = raw
        result['updated'] = re.sub(r'.*([0-9]+) image files updated.*', r'\1',
                raw, flags=re.S)
        if len(raw) == len(result['updated']):
            result['updated'] = 0
        else:
            result['updated'] = int(result['updated'])

        result['created'] = re.sub(r'.*([0-9]+) image files created.*', r'\1',
                raw, flags=re.S)
        if len(raw) == len(result['created']):
            result['created'] = 0
        else:
            result['created'] = int(result['created'])

        result['unchanged'] = re.sub(r'.*([0-9]+) image files unchanged.*',
                r'\1', raw, flags=re.S)
        if len(raw) == len(result['unchanged']):
            result['unchanged'] = 0
        else:
            result['unchanged'] = int(result['unchanged'])

        result['new_name'] = re.sub(r".*'[^']+' --> '([^']+)'.*", r'\1',
                raw, flags=re.S)
        if len(raw) == len(result['new_name']):
            result['new_name'] = ''

        logger.debug('result: updated: ' + str(result['updated']) +
                ' created: ' + str(result['created']) +
                ' unchanged: ' + str(result['unchanged']) +
                ' new_name: ' + str(result['new_name']))
        return result

class ExifToolSingleton(ExifTool, metaclass=singleton.Singleton):
    pass
