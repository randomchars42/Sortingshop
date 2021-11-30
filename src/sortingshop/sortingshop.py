#!/usr/bin/env python3

import signal
import sys
import logging
import logging.config
import pkg_resources
import re
import argparse

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

    def __init__(self, options = []):
        """Initialise UI ... ."""
        self.__ui = wxpython.WxPython()
        self.__tagsets = tagsets.Tagsets(self.__ui)
        self._reset()
        logger.info('initialised')

    def _reset(self):
        """Reset instance variables related to media file handling."""
        self.__medialist = medialist.MediaList()
        self.__current_mediafile = None
        self.__current_source = None
        self.__last_tags = []

    def run(self):
        """Do"""
        # construct
        self.__ui.construct()

        # register events and commands
        self.__ui.register_event('set_working_dir', self.on_set_working_dir)
        self.__ui.register_event('begin_tagging',
                lambda event: self.on_begin_tagging())
        self.__ui.register_event('source_change',
                lambda event: self.load_source(event['name']))
        self.__ui.register_event('sort', lambda event: self.sort())
        self.__ui.register_event('prepare', lambda event: self.prepare_all())

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
        self.__ui.register_command('.', 'short', lambda: self.toggle_tags('.'),
                'toggle the last used tags', 'toggle the previous set of tags')
        self.__ui.register_command('d', 'short', self.toggle_deleted,
                'delete / undelete mediafile', 'moves the mediafile to ' +
                '"./deleted/" or back')
        self.__ui.register_command('h', 'short', lambda: self.flip('h'),
                'flip horizontally', 'flip the mediafile horizontally')
        self.__ui.register_command('v', 'short', lambda: self.flip('v'),
                'flip vertically', 'flip the mediafile vertically')
        self.__ui.register_command('c', 'short', lambda: self.rotate('cw'),
                'rotate clockwise', 'rotate the mediafile clockwise')
        self.__ui.register_command('C', 'short', lambda: self.rotate('ccw'),
                'rotate counterclockwise', 'rotate the mediafile ' +
                'counterclockwise')
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
        self.__ui.register_command(':', 'long', self.jump,
                'load mediafile', 'load the mediafile with the given ' +
                'index or name')
        self.__ui.register_command('s', 'long', self.load_source,
                'load sourcefile', 'load the sourcefile with the given name')

        cfg = config.ConfigSingleton()
        working_dir = cfg.get('Paths', 'working_dir', default='')
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
        cfg.set('Paths', 'working_dir', str(params['working_dir']))

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
        except FileExistsError:
            # the same media file name is used in working_dir and
            # working_dir/deleted
            self.__ui.display_dialog(
                    'File "{}" exists in {} and {}/deleted'.format(
                        self.__medialist.get_duplicate_name(),
                        params['working_dir'], params['working_dir']),
                    dialog_type='ok',
                    callbacks={'ok': lambda: self.__ui.close(True)})
            logger.error('file "{}" exists in {} and {}/deleted'.format(
                        self.__medialist.get_duplicate_name(),
                        params['working_dir'], params['working_dir']))
            self.__medialist = None
            return

        message = 'working directory loaded, found {} mediafiles'.format(
            self.__medialist.get_number_mediafiles())
        logger.debug(message)
        self.__ui.display_message(message)


    def on_begin_tagging(self):
        cfg = config.ConfigSingleton()
        rename = cfg.get('Renaming', 'rename_files', default=True,
                variable_type='boolean')
        prune = cfg.get('Metadata', 'prune_metadata', default=True,
                variable_type='boolean')
        if rename or prune:
            action = 'renamed' if rename else ''
            action += ', ' if rename and prune else ''
            action += 'pruned' if prune else ''
            self.__ui.display_dialog('You are about to begin tagging. Every ' +
                    'file you encounter might be altered (' + action + '). ' +
                    'Those changes are permanent and cannot be undone. ' +
                    'Proceed anyway?',
                    callbacks={'yes': lambda: self.load_mediafile('first')})

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

        mediafile.prepare(tagsets=self.__tagsets)
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
        if user_input == '.':
            tags = self.__last_tags
        else:
            tags = [tag.strip() for tag in user_input.split(',')]
            tags = list(filter(None, tags))
            self.__last_tags = tags

        try:
            self.__current_source.toggle_tags(tags, self.__tagsets)
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
        self.__ui.display_info({'Rating':
            self.__current_source.get_metadata().get('Rating', 0)})
        self.__ui.display_metadata(self.__current_source.get_metadata())

    def jump(self, to):
        """Jump to mediafile NUMBER / NAME.

        Positional arguments:
        to -- index (int) or name (str)
        """
        try:
            to = int(to)
        except ValueError:
            try:
                to = self.__medialist.get_mediafile_index(to)
            except FileNotFoundError:
                self.__ui.display_message('No such file.')
        self.load_mediafile(to)

    def rotate(self, direction='cw'):
        """Rotate by setting the exif flag.

        Operates on the mediafile.

        Keyword arguments:
        direction: clockwise or counterclockwise ("cw"|"ccw")
        """
        # rotate / flip according to exif
        # Value (angles counterclockwise)
        #  1 -> do nothing
        #  2 -> flip horizontally
        #  3 -> rotate 180°
        #  4 -> flip vertically
        #  5 -> flip horizontally, rotate 270°
        #  6 -> rotate 90°
        #  7 -> flip horizontally, rotate 90°
        #  8 -> rotate 270°
        orientation = self.__current_mediafile.get_metadata(
            'Orientation', default='1')

        orientations = ['1','6','3','8']
        flipped_orientations = ['4','7','2','5']

        if orientation in orientations:
            orientation = self._rotate(orientation, direction,
                orientations)
        elif orientation in flipped_orientations:
            orientation = self._rotate(orientation, direction,
                flipped_orientations)

        self.__current_mediafile.set_orientation(orientation)
        self.__ui.display_picture(self.__current_mediafile)
        self.__ui.display_metadata(self.__current_source.get_metadata())

    def _rotate(self, orientation, direction, orientations):
        # to rotate counterclockwise the order of orientations just needs
        # to be reversed
        if direction == 'ccw':
            orientations.reverse()

        # get the index of the current orientation
        index = orientations.index(orientation)
        # and move one position forwards (wrap around if necessary)
        if index == len(orientations) - 1:
            index = 0
        else:
            index = index + 1
        return orientations[index]


    def flip(self, direction='v'):
        """Flip by setting the exif flag if possible.

        Not all orientations may be flipped this way.
        Operates on the mediafile.

        Keyword arguments:
        direction: vertically or horizontally ("v"|"h")
        """
        orientation = self.__current_mediafile.get_metadata(
            'Orientation', default='1')

        if direction == 'v':
            orientation = {
                '1':'4', '4':'1',
                '3':'2', '2':'3',
                '5':'6', '6':'5',
                '8':'7', '7':'8'
                }[orientation]
        elif direction == 'h':
            orientation =  {
                '1':'2', '2':'1',
                '4':'3', '3':'4',
                '5':'8', '8':'5',
                '7':'6', '6':'7'
                }[orientation]

        self.__current_mediafile.set_orientation(orientation)
        self.__ui.display_picture(self.__current_mediafile)

    def sort(self):
        """Check each mediafile for the sorting tag and sort accordingly.

        The sorting tag is defined in the configuration.
        """
        cfg = config.ConfigSingleton()

        working_dir = cfg.get('Paths', 'working_dir', default = '')
        if working_dir == '':
            logger.error('working_dir not set')
            raise ValueError
        else:
            working_dir = Path(working_dir)

        regex = cfg.get('Sorting', 'sorting_tag_regex', default = '')
        if regex == '':
            logger.error('Missing sorting_tag_regex in config')
            raise ValueError

        sub = cfg.get('Sorting', 'sorting_tag_sub', default = '')
        if regex == '':
            logger.error('Missing sorting_tag_sub in config')
            raise ValueError

        errors = []

        mediafiles = self.__medialist.get_mediafiles()
        # scan all mediafiles
        for mediafile in mediafiles:
            if mediafile.is_deleted():
                # skip "deleted files
                continue
            logger.debug('Scanning "{}"'.format(mediafile.get_name()))
            # sorting tag for this mediafile
            target = ''
            source = mediafile.get_primary_source()
            source.load()
            for tag in source.get_taglist().get_tags():
                target, n = re.subn(regex, sub, tag)
                if n > 0:
                    # we found a sorting tag
                    logger.debug('Matched target "{}"'.format(target))
                    source.unload()
                    break
                else:
                    target = ''
            source.unload()

            # no sorting tag found
            if target == '':
                errors.append('No sorting tag found in "{}"'.format(
                    source.get_path()))
                # skip to next mediafile
                continue

            # create destination
            destination = working_dir / Path(target)
            # create the target directory
            try:
                destination.mkdir(parents = True, exist_ok = True)
            except PermissionError:
                errors.append('Insufficient permissions to create "{}"'.format(
                    destination))
                # skip to next mediafile
                continue
            except FileExistsError:
                errors.append('"{}" is not a directory'.format(destination))
                # skip to next mediafile
                continue

            # move the file
            mediafile.move(destination)

        # display errors
        errors = list(set(errors))
        for error in errors:
            logger.info(error)
        if len(errors) > 0:
            self.__ui.display_message("\n".join(errors))
        # rescan working dir
        logger.debug('Initiate re-scan of "{}"'.format(str(working_dir)))
        self.__ui.set_working_dir(str(working_dir))

    def prepare_all(self):
        """Check each mediafile and prepare it.

        The sorting tag is defined in the configuration.
        """
        cfg = config.ConfigSingleton()

        working_dir = cfg.get('Paths', 'working_dir', default = '')
        if working_dir == '':
            logger.error('working_dir not set')
            raise ValueError
        else:
            working_dir = Path(working_dir)

        errors = []

        # scan all mediafiles
        for i in range(self.__medialist.get_number_mediafiles()):
            mediafile = self.__medialist.get_mediafile(i)
            logger.debug('Scanning "{}"'.format(mediafile.get_name()))
            try:
                mediafile.prepare(self.__tagsets)
            except FileNotFoundError:
                errors.append(
                        'Could not create a sidecar for "{}" (no metada)'.format(
                            mediafile.get_name()))
        # display errors
        errors = list(set(errors))
        for error in errors:
            logger.info(error)
        if len(errors) > 0:
            self.__ui.display_message("\n".join(errors))
        self.__ui.display_message("Preparation of all files finished.")

def main():
    """Run the application.

    Configure logging and set correct ExifTool executable (packaged if it exists
    or system).

    Raises FileNotFoundError if no ExifTool executable could be detected.
    """
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

    cfg = config.ConfigSingleton()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--options',
        help='arbitrary configuration(s) as could be found in the ini-file ' +
            'formatted like SECTION1.option1=val1@@SECTION2.option4=val2@@...' +
            ', e.g., Metadata.soft_check=true@@Renaming.rename_files=false, ' +
            '"@@" serves as a separator',
        action='store',
        default='',
        type=str)
    parser.add_argument(
        '-d', '--working_dir',
        help='your working directory (where the pictures are) [None]',
        action='store',
        type=str,
        default="")
    parser.add_argument(
        '-v', '--verbosity',
        help='turn on debug mode',
        action='count',
        default=0)

    args = parser.parse_args()

    if not args.options == '':
        for option in args.options.split('@@'):
            try:
                section, rest = option.split('.', 1)
                option, value = rest.split('=', 1)
                cfg.set(section, option, value)
            except:
                logger.error('did not understand option "{}"'.format(option))

    if not args.working_dir == '':
        cfg.set('Paths', 'working_dir', args.working_dir)

    verbosity = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
    log.config['handlers']['console']['level'] = verbosity[args.verbosity]
    log.config['loggers']['__main__']['level'] = verbosity[args.verbosity]
    log.config['loggers']['sortingshop']['level'] = verbosity[args.verbosity]

    logging.config.dictConfig(log.config)

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
