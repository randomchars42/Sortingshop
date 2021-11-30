#!/usr/bin/env python3

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class UI():
    """Abstract class for user interfaces (GUI/CLI/?) to implement.

    The following methods need to be implemented or else an NotImplementedError
    will be raised:
     - display_*
     - run
     - construct
    """
    def __init__(self):
        """Initialise member variables."""
        self._short_commands = {}
        self._long_commands = {}
        self._events = {}
        self._working_dir = None

    def register_command(self, command, command_type, callback, label, info):
        """Register a command and callback.

        "Short" commands are single letter commands without any arguments. The
        callback function will be invoked with callback().

        "Long" commands are single letter commands which recieve an arbitrary
        amount of arguments. The callback function will be invoked with
        callback(arguments).

        Positional arguments:
        command -- the command to trigger callback (string)
        command_type -- either "short" or "long" (string)
        callback -- method to call on command
        label -- short label for the command displayed to the user (string)
        info -- longer description of what the command does, potentially
                displayd to the user (string)
        """
        if command_type == 'short':
            self._short_commands[command] = {
                    'callback': callback, 'label': label, 'info': info}
            logger.debug('short command "{}" registered'.format(command))
        elif command_type == 'long':
            self._long_commands[command] = {
                    'callback': callback, 'label': label, 'info': info}
            logger.debug('long command "{}" registered'.format(command))
        else:
            logger.error(
                'Command {} not registered (invalid command type: {})'.format(
                    command, command_type))

    def process_command(self, raw_command):
        """Process command and call appropriate callback for command.

        Return True if the raw_command is processed (either dropped or the
        appropriate command was called) and the input may be cleared.
        Return False if further input is required.
        True / False do not necessarily indicate a valid command as an invalid
        letter will also produce True (i.e. processed / dropped, clear input).

        Note: A long command needs to end with "\n" to be recognised as
        complete.

        Positional arguments:
        raw_command -- the command string as typed by the user, arguments are
                       separated from the command by a blank, arguments are
                       separated from each other by a comma
        """

        # three cases
        # 1) raw_command is a single letter
        #     - it's a short command -> call function and return True
        #     - it's a long command -> return False and wait until 2)
        #     - none of the above -> return True (processed & dropped) and wait
        # 2) raw_command is a complete command to be evaluated ending with "\n"
        #     - it's a long command -> call the function and return True
        #     - it's invalid -> return True (processed & dropped)
        # 3) raw_command contains multiple characters but is not finished (no
        #    final "\n"
        #     - might become one of the possibilities in 2) -> return False and
        #       wait

        if len(raw_command) == 1:
            # case 1
            if raw_command in self._long_commands:
                # wait for the command to end
                logger.debug('Command "{}" begun'.format(raw_command))
                return False
            elif raw_command in self._short_commands:
                logger.debug('Command "{}" called'.format(raw_command))
                self._short_commands[raw_command]['callback']()
                # command processed
                return True
            else:
                logger.debug('Invalid command ("{}")'.format(raw_command))
                # drop
                return True
        elif len(raw_command) > 1 and raw_command[-1] == "\n":
            # case 2
            parts = raw_command.split(' ',1)

            if len(parts) == 1:
                # missing space between command
                logger.debug('Malformed command ("{}")'.format(raw_command))
                # drop
                return True

            command = parts[0]

            if not command in self._long_commands:
                logger.debug('Invalid command ("{}")'.format(command))
                # drop
                return True

            logger.debug('Command "{}" finished'.format(raw_command.strip()))
            # extract arguments
            arguments = parts[1].strip()

            if arguments == '':
                logger.debug('No valid arguments in ("{}"), dropped'.format(
                    arguments))
                # drop
                return True

            # call
            logger.debug('Command "{}" called with arguments: {}'.format(
                command, arguments))
            self._long_commands[command]['callback'](arguments)
            return True
        else:
            # case 3
            logger.debug('Unfinished command ("{}"), waiting'.format(
                raw_command))
            # do not drop
            return False

    def register_event(self, event, callback):
        """Register an event and callback.

        Positional arguments:
        event -- the event to trigger callback (string)
        callback -- method to call on event
        """
        try:
            self._events[event].append(callback)
        except KeyError:
            self._events[event] = [callback]

    def fire_event(self, event, params={}):
        """Call callback for event.

        Raises ValueError if no callbacks are registered.

        Positional arguments:
        event -- the event to trigger callback (string)

        Keyword arguments:
        params -- dict of additional arguments passed to callback
        """
        try:
            logger.debug('fire event: {}'.format(event))
            for callback in self._events[event]:
                callback(params)
        except KeyError as error:
            raise ValueError('No listeners for event ("{}")'.format(event))

    def set_working_dir(self, working_dir):
        """Set the working directory and fire "set_working_directory".

        Raises:
         - FileNotFoundError if the given directory doesn't exist
         - NotADirectoryError if not a directory

        Positional arguments:
        working_dir -- the working directory (string)
        """
        if working_dir.strip() == '':
            return
        working_dir = Path(working_dir)
        if not working_dir.exists():
            logger.error('Directory "{}" not found'.format(working_dir))
            raise FileNotFoundError
        if not working_dir.is_dir():
            logger.error('Path not a "{}" directory'.format(working_dir))
            working_dir = working_dir.parent()
            #raise NotADirectoryError
        logger.debug('set working_dir: "{}"'.format(str(working_dir)))
        self._working_dir = working_dir
        self.fire_event('set_working_dir', {'working_dir': working_dir})

    def construct(self):
        raise NotImplementedError('method "contruct" not implemented')

    def run(self):
        raise NotImplementedError('method "run" not implemented')

    def display_tagsets(self, origin, tagsets):
        raise NotImplementedError('method "display_tagsets" not implemented')

    def display_shortcuts(self, shortcuts):
        raise NotImplementedError('method "display_shortcuts" not implemented')

    def display_picture(self, picture_path = None):
        """Display the given picture.

        This is an abstract method. If no path is given consider loading a
        default.

        Keyword arguments:
        picture_path -- path to the picture (string / Path)
        """
        raise NotImplementedError('method "display_pictures" not implemented')

    def display_sources(self, sources):
        raise NotImplementedError('method "display_sources" not implemented')

    def clear(self):
        raise NotImplementedError('method "clear" not implemented')

    def display_info(self, metadata, index=-1, n=-1):
        raise NotImplementedError('method "display_info" not implemented')

    def display_metadata(self, metadata):
        raise NotImplementedError('method "display_metadata" not implemented')

    def display_tags(self, metadata):
        raise NotImplementedError('method "display_tags" not implemented')

    def display_deleted_status(self, is_deleted):
        raise NotImplementedError('method "display_deleted" not implemented')

    def display_message(self, message):
        raise NotImplementedError('method "display_message" not implemented')

    def display_dialog(self, message, dialog_type="yesno"):
        raise NotImplementedError('method "display_dialog" not implemented')

    def close(self, force=True):
        raise NotImplementedError('method "close" not implemented')
