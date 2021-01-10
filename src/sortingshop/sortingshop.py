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
from .media import taglist
from .media import tagsets
from .ui import wxpython
from .log import log

logger = logging.getLogger(__name__)

class Sortingshop():
    """"""

    def __init__(self):
        """Initialise UI ... ."""
        self.__ui = wxpython.WxPython()
        self.__tagsets = tagsets.Tagsets()
        self._reset()
        logger.info('initialised')

    def _reset(self):
        """Reset instance variables related to media file handling."""
        self.__medialist = None
        self.__current_mediafile = None
        self.__current_source = None

    def run(self, working_dir=''):
        """Do"""
        # construct
        self.__ui.construct()

        # register events and commands
        self.__ui.register_event('set_working_dir', self.on_set_working_dir)
        self.__ui.register_event('source_change',
                lambda event: self.load_source(event['name']))

        self.__ui.register_command('n', 'short', self.load_next_mediafile,
                'next mediafile', 'display the next mediafile')
        self.__ui.register_command('p', 'short', self.load_previous_mediafile,
                'previous mediafile', 'display the previous mediafile')
        #self.__ui.register_command('A', 'short', self.load_all_sources,
        #        'next sidecar', 'display tags from the next source')
        self.__ui.register_command('N', 'short', self.load_next_source,
                'next sidecar', 'display tags from the next source')
        self.__ui.register_command('P', 'short', self.load_previous_source,
                'previous sidecar', 'display tags from the previous source')
        self.__ui.register_command('t', 'long', self.toggle_tags,
                'toggle TAG1,TAG2', 'sets the tag if it is not present, else ' +
                'removes it')
        self.__ui.register_command('d', 'short', self.toggle_deleted,
                'delete / undelete mediafile', 'moves the mediafile to ' +
                '"./deleted/" or back')
        self.__ui.register_command('r', 'short', lambda: self.set_rating(-1),
                'rating: rejected', 'rate the mediafile as rejected')
        self.__ui.register_command('0', 'short', lambda: self.set_rating(0),
                'rating: 0', 'rate the mediafile as a 0')
        self.__ui.register_command('1', 'short', lambda: self.set_rating(1),
                'rating: 1', 'rate the mediafile as a 1')
        self.__ui.register_command('2', 'short', lambda: self.set_rating(2),
                'rating: 2', 'rate the mediafile as a 2')
        self.__ui.register_command('3', 'short', lambda: self.set_rating(3),
                'rating: 3', 'rate the mediafile as a 3')
        self.__ui.register_command('4', 'short', lambda: self.set_rating(4),
                'rating: 4', 'rate the mediafile as a 4')
        self.__ui.register_command('5', 'short', lambda: self.set_rating(5),
                'rating: 5', 'rate the mediafile as a 5')
        self.__ui.register_command(':', 'long', self.load_mediafile,
                'load mediafile', 'load the mediafile with the given index')
        self.__ui.register_command('.', 'long', self.load_source,
                'load sourcefile', 'load the sourcefile with the given name')

        if working_dir == '':
            cfg = config.ConfigSingleton()
            working_dir = cfg.get('Paths', 'working_dir', default='')
            print(working_dir)
        self.__ui.set_working_dir(working_dir)

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

        # load tagsets
        try:
            self.__tagsets.load_tagsets()
        except PermissionError as error:
            self.__ui.display_message(
                    'Insufficient rights to open tagsets file')
            logger.error(error, exc_info=True)

        self.__ui.display_tagsets(self.__tagsets.get_tagsets())
        self.load_mediafile('first')

    def load_mediafile(self, position):
        """ Load a mediafile and check if it has been removed since startup.

        After set_working_dir the working directory is scanned and a list is
        built. If the user (re)moves files from that directory the change
        will not be detected so this function checks if the requested file
        (first, last, next, previous, current, INDEX) is available.

        Positional arguments:
        position -- string indicating the requested file ("first", "last",
            "next", "previous", "current", INDEX)
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
                logger.debug('load {}'.format(mediafile.get_name()))
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
        self.__current_mediafile = mediafile
        self.__ui.clear()
        self.__ui.display_picture(mediafile)
        self.__ui.display_sources(mediafile.get_sources())
        self.__ui.display_info(mediafile.get_metadata(),
                index = self.__medialist.get_current_index(),
                n = self.__medialist.get_number_mediafiles())
        self.__ui.display_deleted_status(mediafile.is_deleted())

        self.__current_source = None
        self.load_source('default')

    def load_next_mediafile(self):
        logger.debug('next picture')
        self.load_mediafile('next')

    def load_previous_mediafile(self):
        logger.debug('previous picture')
        self.load_mediafile('previous')

    def load_source(self, position):
        """ Load a source (and check if it has been removed since startup).

        After set_working_dir the working directory is scanned and a list is
        built. If the user (re)moves files from that directory the change
        will not be detected so this function checks if the requested sidecar
        (first, last, next, previous, current, INDEX) is available.

        Positional arguments:
        position -- string indicating the requested file ("first", "last",
            "next", "previous", "current", INDEX)
        """
        logger.debug('load source {}'.format(position))
        source_found = False
        abort = False
        files_not_found = 0

        # - try to load the file
        # - if no file is found try again (the next / previous / new first /
        #   new last)
        # - if "current" is requested or no file remains in the list display a
        #   default text
        while source_found is False and abort is False:
            try:
                source = self.__current_mediafile.get_source(position)
                logger.debug('load {}'.format(source.get_name()))
            except FileNotFoundError as error:
                logger.error('{} source file not found'.format(position))
                if position == 'current':
                    self.__ui.display_message('Current source file not found ' +
                        'anymore. Did you just remove it?')
                    # leave loop display default and continue...
                    abort = True
                    pass
                # count files
                files_not_found += 1
            except IndexError as error:
                self.__ui.display_message('Media file not found anymore. ' +
                        'Did you just remove it?')
                self.load_next_mediafile()
            else:
                source_found = True

        if files_not_found > 0:
            self.__ui.display_message('{} sidecar file(s) not found ' +
                    'anymore.'.format(str(files_not_found)))

        self.__current_source = source
        self.__ui.display_metadata(source.get_metadata())
        self.__ui.display_info(
                {'Rating': source.get_metadata().get('Rating', 0)})
        self.__ui.display_tags(source.get_taglist())

    def load_next_source(self):
        logger.info('next source')
        self.load_source('next')

    def load_previous_source(self):
        logger.info('previous source')
        self.load_source('previous')

    def toggle_tags(self, user_input):
        """Add / remove tags.

        The user may input a list of tags and or abbreviations which will be
        expanded with the help of tagsets.
        """
        # expand abbreviations entered by the user
        tags = []
        for part in user_input:
            # if a non-empty array is returned the part of the user input was an
            # abbreviation
            # if no matching tagset is found treat the part as a new tag
            tagset = self.__tagsets.get_tagset(part)
            if len(tagset) > 0:
                logger.debug('extended abbreviation "{}" -> {}'.format(
                    part, ','.join(tagset)))
                tags.extend(tagset)
            else:
                tags.append(part)

        # filter duplicates & sort
        tags = list(set(tags))
        tags.sort()
        logger.info('toggle tags: {}'.format(','.join(tags)))

        try:
            self.__current_source.toggle_tags(tags)
        except ChildProcessError:
            self.__ui.display_message('Tags were not updated.')
        except FileNotFoundError:
            self.__ui.display_message('File not found anymore.')
        self.__ui.display_tags(self.__current_source.get_taglist())

    def toggle_deleted(self):
        logger.info('delete / undelete mediafile')
        try:
            self.__current_mediafile.toggle_deleted()
        except FileExistsError:
            # something has been messed up after creating the medialist
            # consider shutting down the app
            message = 'File "{}" exists in "./" and "./deleted/".'.format(
                    str(self.__current_mediafile.get_path()))
            self.__ui.display_message(message)
        except ValueError:
            self.__ui.display_message('Oops... something went wrong.')
        except PermissionError:
            self.__ui.display_message(
                    'Seems you don\'t have proper permissions.')
        except FileNotFoundError:
            self.__ui.display_message('File not found anymore.')
        self.__ui.display_deleted_status(self.__current_mediafile.is_deleted())

    def set_rating(self, rating):
        try:
            self.__current_source.set_rating(rating)
        except ValueError:
            self.__ui.display_message('Oops... something went wrong.')
        except ChildProcessError:
            self.__ui.display_message('Rating was not updated.')
        except FileNotFoundError:
            self.__ui.display_message('File not found anymore.')
        self.__ui.display_metadata({'Rating':
            self.__current_source.get_metadata().get('Rating', 0)})

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
