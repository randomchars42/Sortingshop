#!/usr/bin/env python3

import logging
from pathlib import Path
import wx
from wx.lib.dialogs import ScrolledMessageDialog
import time
import pkg_resources

from . import ui
from .. import config

logger = logging.getLogger(__name__)

class WxPython(ui.UI):
    """A WxPython Phoenix GUI for Sortingshop.

    It consists of a multiple pages with one homepage to access the different
    functions of the app.

    This class only constructs and layouts the frame. Each Page has its own
    class.
    """
    def __init__(self):
        """Initialise instance variables and the wx.App."""
        super(WxPython, self).__init__()
        self.__app = wx.App(False)
        self.__pages = {}
        self.__homepage = 'home'
        self.__current_page = self.__homepage
        self.__last_page = ''
        self.__metadata = {}
        self.clear()

    def construct(self):
        """Construct the frame and its layout."""
        self.register_command('H', 'short', self.display_help,
                'display this help', 'display this help')
        # the application frame (what you see as a "window")
        self.__frame = wx.Frame(parent=None, id=wx.ID_ANY, title='Sortingshop')
        path = Path(pkg_resources.resource_filename(__name__, 'resources/sosho.ico'))
        self.__frame.SetIcon(wx.Icon(str(path), wx.BITMAP_TYPE_ICO))
        self.__frame.Show()
        # add a sizer which will later be used to resize the frame according to
        # its content
        self.__frame_sizer = wx.BoxSizer(wx.VERTICAL)
        self.__frame.SetSizer(self.__frame_sizer)

        # every frame should have a panel for visual consistency
        # it should scale with the frame
        panel = wx.Panel(parent=self.__frame)
        self.__frame_sizer.Add(panel, flag=wx.EXPAND, proportion=1)

        # the main_panel will be divided in an area for the pages and an
        # optional button bar at the bottom
        #  __________________________
        # |                          |
        # |                          |
        # |                          |
        # |                          |
        # |     Pages                |
        # |                          |
        # |                          |
        # |                          |
        # |__________________________|
        # |                          |
        # |     Buttons (optional)   |
        # |__________________________|
        #

        # sizer to organize the layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        # add pages

        # the homepage
        homepage = HomePage(panel)
        sizer.Add(homepage, flag=wx.EXPAND, proportion=1)
        self.__pages[self.__homepage] = homepage
        # set actions to events
        homepage.bind_to_button('prepare', lambda event: self.fire_event('prepare'))
        homepage.bind_to_button('tag', lambda event: self._begin_tagging())
        homepage.bind_to_dir_picker(self._pick_working_dir_handler)
        homepage.bind_to_button('sort', lambda event: self.fire_event('sort'))

        # the page used to tag individual media files
        tag_page = TagPage(panel, layout=wx.HORIZONTAL,
                callback_on_back=self._display_previous_page)
        sizer.Add(tag_page, flag=wx.EXPAND, proportion=1)
        self.__pages['tag'] = tag_page
        tag_page.set_command_processor(self.process_command)
        tag_page.set_source_picker_action(
                lambda event: self.fire_event('source_change',
                    {'name': event.GetString()}))
        tag_page.bind_to_button('update_local', lambda event: self.fire_event(
            'update_tagsets',
            {'origin': 'local',
                'text': self.__pages['tag'].get_tagsets('local')}))
        tag_page.bind_to_button('update_global', lambda event: self.fire_event(
            'update_tagsets',
            {'origin': 'global',
                'text': self.__pages['tag'].get_tagsets('global')}))
        tag_page.bind_to_button('save_local', lambda event: self.fire_event(
            'save_tagsets',
            {'origin': 'local',
                'text': self.__pages['tag'].get_tagsets('local')}))
        tag_page.bind_to_button('save_global', lambda event: self.fire_event(
            'save_tagsets',
            {'origin': 'global',
                'text': self.__pages['tag'].get_tagsets('global')}))

        # prepare for display

        # get a minimum size for the frame
        # as the tag page is the largest page use its size
        size = self.__pages['tag'].GetEffectiveMinSize()
        self.__frame.SetMinSize(size)

        # hide all pages
        for page in self.__pages:
            self.__pages[page].Hide()
        # display only the homepage and resize the frame to fit
        self._display_page(self.__homepage)

    def run(self):
        """Run the app's MainLoop."""
        self.__app.MainLoop()

    def close(self, force=True):
        """Close the app."""
        self.__frame.Destroy()

    def _display_previous_page(self, event):
        """Display the last page.

        Positional arguments:
        event -- the event on which this function is called
        """
        self._display_page(self.__last_page)

    def _display_page(self, page):
        """Display (show) a pre-built page and hide the current one.

        Positional arguments:
        page -- the page to display (string)
        """
        if not page in self.__pages:
            raise ValueError('No such page ("{}")'.format(page))

        # hide the current page and display the requested one
        self.__last_page = self.__current_page
        self.__current_page = page
        self.__pages[self.__last_page].hide_page()
        self.__pages[self.__current_page].show_page()

        # resize the frame to show all currently displayed widgets
        self.__frame_sizer.Layout()
        self.__frame.Fit()

    def display_help(self):
        message = ''
        for cmd, info in self._short_commands.items():
            message += cmd + ': ' + info['info'] + "\n"
        for cmd, info in self._long_commands.items():
            message += cmd + ' XXX: ' + info['info'] + "\n"
        self.display_message(message)

    def display_tagsets(self, origin, tagsets):
        self.__pages['tag'].load_tagsets(origin, tagsets)

    def display_shortcuts(self, shortcuts):
        raise NotImplementedError('method "display_shortcuts" not implemented')

    def display_picture(self, mediafile = None):
        """Display the given picture.

        Keyword arguments:
        mediafile -- MediaFile
        """
        self.__pages['tag'].load_image(mediafile)

    def display_sources(self, sources):
        """Display the sources.

        Positional arguments:
        sources -- list
        """
        self.__pages['tag'].load_sources(sources)

    def clear(self):
        """Prepare for the next mediafile."""
        self.__metadata['index'] = -1
        self.__metadata['n'] = self.__metadata.get('n', -1)
        self.__metadata['name'] = ''
        self.__metadata['rating'] = 0
        self.__metadata['date'] = ''
        self.__metadata['deleted'] = False

    def _begin_tagging(self):
        self.fire_event('begin_tagging')
        self._display_page('tag')

    def display_metadata(self, metadata):
        self.__pages['tag'].load_metadata(metadata)

    def display_info(self, metadata, index=-1, n=-1):
        self.__metadata['index'] = index if index > -1 else self.__metadata['index']
        self.__metadata['n'] = n if n != -1 else self.__metadata['n']
        self.__metadata['name'] = metadata.get('FileName',
                self.__metadata['name'])
        self.__metadata['rating'] = metadata.get('Rating',
                self.__metadata['rating'])
        self.__metadata['date'] = metadata.get('CreateDate',
                self.__metadata['date'])
        self.__pages['tag'].load_info(self.__metadata)

    def display_tags(self, taglist):
        self.__pages['tag'].load_tags(taglist)

    def display_deleted_status(self, is_deleted):
        self.__metadata['deleted'] = is_deleted
        self.__pages['tag'].load_info(self.__metadata)

    def display_message(self, message):
        self.display_dialog(message, dialog_type = 'ok')

    def display_dialog(self, message, caption='Info', dialog_type='yesno',
            callbacks={}, scrollable=None):
        """Display a configurable dialog."""
        style = None

        if dialog_type == 'yesno':
            style = wx.ICON_QUESTION|wx.YES_NO|wx.CANCEL
        elif dialog_type == 'okcancel':
            style = wx.ICON_QUESTION|wx.OK|wx.CANCEL
        else:
            style = wx.ICON_INFORMATION|wx.OK

        if scrollable is None:
            scrollable = message.count("\n") > 4

        if scrollable:
            dialog = ScrolledMessageDialog(
                    self.__frame, message, caption = caption, style =  style)
        else:
            dialog = wx.MessageDialog(
                    self.__frame, message, caption = caption, style =  style)

        clicked = dialog.ShowModal()

        # find and execute the apropriate callback:
        # map wx.ID_??? against the dictionary passed as param to this function
        # if any key is not defined "do" will become an empty lambda expression
        do = {
                wx.ID_YES: callbacks.get('yes', lambda: None),
                wx.ID_NO: callbacks.get('no', lambda: None),
                wx.ID_CANCEL: callbacks.get('cancel', lambda: None),
                wx.ID_OK: callbacks.get('ok', lambda: None)
                }.get(clicked, lambda: None)()

        dialog.Destroy()

    def _pick_working_dir_handler(self, event):
        working_dir = event.GetPath()
        self.set_working_dir(working_dir)

    def set_working_dir(self, working_dir):
        if working_dir.strip() == '':
            return
        working_dir_path = Path(working_dir)
        if not working_dir_path.exists():
            logger.error('Directory "{}" not found'.format(working_dir))
            return
        if not working_dir_path.is_dir():
            logger.error('Path not a "{}" directory'.format(working_dir))
            return
        #if working_dir == str(self._working_dir):
        #    return
        self.__pages[self.__homepage].set_dir_picker_path(working_dir)
        super(WxPython, self).set_working_dir(working_dir)

class Page(wx.Panel):
    """Base class for all pages of the app."""

    def __init__(self, parent, layout=wx.VERTICAL, callback_on_back=None,
            *args, **kwargs):
        """Initialise panel and instance variables and add a BoxSizer.

        The vertical BoxSizer is available via _main_sizer.

        Positional arguments:
        parent -- wx.Window that serves as parent
        """
        wx.Panel.__init__(self, parent=parent, *args, **kwargs)
        master_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(master_sizer)

        # the sizer used for page layout
        self._sizer = wx.BoxSizer(layout)
        master_sizer.Add(self._sizer, flag=wx.EXPAND, proportion=1)
        # add this sizer to ensure buttons are at the bottom
        self.__bar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        master_sizer.Add(self.__bar_sizer, flag=wx.ALIGN_RIGHT, proportion=0)

        self._buttons = {}

        if not callback_on_back is None:
            button_back = wx.Button(parent=self, label='Back')
            button_back.Bind(event=wx.EVT_BUTTON, handler=callback_on_back)
            self.__bar_sizer.Add(button_back)
            self._buttons['back'] = button_back

    def show_page(self):
        """Extensible wrapper around window.Show."""
        self.Show()

    def hide_page(self):
        """Extensible wrapper around window.Hide."""
        self.Hide()

    def bind_to_button(self, button, callback):
        """Bind a callback to a button on this page.

        Positional arguments:
        button -- the name of the button (string)
        callback -- function to call
        """
        if not button in self._buttons:
            raise ValueError('No such button ("{}")'.format(button))
        self._buttons[button].Bind(event=wx.EVT_BUTTON, handler=callback)

class HomePage(Page):
    """ The entry page lets the user choose the directory and what to do."""

    def __init__(self, parent, *args, **kwargs):
        """Construct the page.

        Positional arguments:
        parent -- wx.Window that serves as parent
        """
        super(HomePage, self).__init__(parent, *args, **kwargs)

        # this is the homepage, a back button makes no sense
        self._show_buttons = False
        # center buttons vertically
        self._sizer.AddStretchSpacer(prop=1)

        self.__dir_picker = wx.DirPickerCtrl(parent=self, path=str(Path.home()),
              message='Choose a directory',
              style=wx.DIRP_DIR_MUST_EXIST|wx.DIRP_SMALL|wx.DIRP_USE_TEXTCTRL)
        self._sizer.Add(self.__dir_picker, flag=wx.EXPAND)

        self._buttons['prepare'] = wx.Button(parent=self,
                label='Prepare mediafiles (e.g. rename, prune)')
        self._sizer.Add(self._buttons['prepare'], flag=wx.EXPAND)

        self._buttons['tag'] = wx.Button(parent=self,
                label='Start taggging files')
        self._sizer.Add(self._buttons['tag'], flag=wx.EXPAND)

        self._buttons['sort'] = wx.Button(parent=self,
                label='Sort mediafiles by tags')
        self._sizer.Add(self._buttons['sort'], flag=wx.EXPAND)

        # center buttons vertically
        self._sizer.AddStretchSpacer(prop=1)

    def bind_to_dir_picker(self, callback):
        """Bind a callback to the directory picker on this page.

        Positional arguments:
        callback -- function to call
        """
        self.Bind(wx.EVT_DIRPICKER_CHANGED, callback)

    def set_dir_picker_path(self, path):
        """Set a new starting path for the dir picker.

        Positional arguments:
        path -- string the path
        """
        self.__dir_picker.SetPath(str(path))
        #self.__dir_picker.SetInitialDirectory(path)

class TagPage(Page):
    def __init__(self, parent, *args, **kwargs):
        """Construct the page and initiate instance variables.

        Positional arguments:
        parent -- wx.Window that serves as parent
        """
        super(TagPage, self).__init__(parent, *args, **kwargs)

        cfg = config.ConfigSingleton()

        # the max height and width
        self.__max_size = cfg.get('UI', 'image_max_size', default=400,
                variable_type='int')

        # construct

        # columns
        self.__column_1 = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self.__column_1, flag=wx.EXPAND, proportion=2)
        self.__column_2 = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self.__column_2, flag=wx.EXPAND, proportion=1)
        self.__column_3 = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self.__column_3, flag=wx.EXPAND, proportion=1)
        self.__column_4 = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self.__column_4, flag=wx.EXPAND, proportion=1)

        # column 1

        # image
        # placeholder where we will load the image into
        image = wx.Image(self.__max_size, self.__max_size)
        self.__image = wx.StaticBitmap(self, id=wx.ID_ANY,
                bitmap=wx.Bitmap(image))
        self.__column_1.Add(self.__image, flag=wx.CENTER)

        # metadata
        self.__info_panel = wx.StaticText(self, id=wx.ID_ANY,
                style=wx.ST_NO_AUTORESIZE|wx.ALIGN_CENTRE_HORIZONTAL)
        self.__column_1.Add(self.__info_panel, flag=wx.EXPAND, proportion=0)

        # column 2

        # source picker
        self.__source_picker = wx.Choice(self, id=wx.ID_ANY)
        self.__column_2.Add(self.__source_picker, flag=wx.EXPAND, proportion=0)

        # command entry
        self.__command_entry = CommandEntry(parent=self)
        self.__column_2.Add(self.__command_entry, flag=wx.EXPAND, proportion=0)

        # metadata
        ctrl_size = cfg.get('UI', 'metadata_field_size_vertical', default=300,
                variable_type='int')
        self.__metadata = wx.TextCtrl(self, id=wx.ID_ANY, size=(-1,ctrl_size),
                style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.__column_2.Add(self.__metadata, flag=wx.EXPAND, proportion=1)

        # column 3

        # tagsets
        self._tagsets = {}

        self._tagsets['local'] = wx.TextCtrl(self, id=wx.ID_ANY,
                style=wx.TE_MULTILINE)
        self.__column_3.Add(self._tagsets['local'], flag=wx.EXPAND, proportion=1)

        self._buttons['update_local'] = wx.Button(parent=self,
                label='Update local taglists')
        self.__column_3.Add(self._buttons['update_local'], flag=wx.EXPAND)

        self._buttons['save_local'] = wx.Button(parent=self,
                label='Save local taglists')
        self.__column_3.Add(self._buttons['save_local'], flag=wx.EXPAND)

        self._tagsets['global'] = wx.TextCtrl(self, id=wx.ID_ANY,
                style=wx.TE_MULTILINE)
        self.__column_3.Add(self._tagsets['global'], flag=wx.EXPAND, proportion=2)

        self._buttons['update_global'] = wx.Button(parent=self,
                label='Update global taglists')
        self.__column_3.Add(self._buttons['update_global'], flag=wx.EXPAND)

        self._buttons['save_global'] = wx.Button(parent=self,
                label='Save global taglists')
        self.__column_3.Add(self._buttons['save_global'], flag=wx.EXPAND)


        # column 4

        # metadata
        self.__metadata_panel = wx.TextCtrl(self, id=wx.ID_ANY,
                style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.__column_4.Add(self.__metadata_panel, flag=wx.EXPAND, proportion=1)

        # finished construction

        # load a default image
        self.load_image()

    def show_page(self):
        """Show the page and focus the CommandEntry."""
        super(TagPage, self).show_page()
        self.focus_command_entry()

    def load_image(self, mediafile = None):
        """Load the image, scale it down and display it.

        Keyword arguments:
        mediafile -- MediaFile
        """

        if mediafile is None:
            path = Path(pkg_resources.resource_filename(__name__,
                'resources/default.jpeg'))
        else:
            path = str(mediafile.get_path())

        image = wx.Image(str(path), type=wx.BITMAP_TYPE_ANY)
        # rotate / flip according to exif
        # Value (angles clockwise)
        #  0 -> do nothing
        #  1 -> do nothing
        #  2 -> flip horizontally
        #  3 -> rotate 180°
        #  4 -> flip vertically
        #  5 -> flip horizontally, rotate 270°
        #  6 -> rotate 90°
        #  7 -> flip horizontally, rotate 90°
        #  8 -> rotate 270°
        if not mediafile is None:
            orientation = mediafile.get_metadata('Orientation', default='1')
            if orientation == '2':
                image = image.Mirror(horizontally=False)
            elif orientation == '3':
                image = image.Rotate180()
            elif orientation == '4':
                image = image.Mirror(horizontally=True)
            elif orientation == '5':
                image = image.Mirror(horizontally=True)
                image = image.Rotate90(clockwise=False)
            elif orientation == '6':
                image = image.Rotate90(clockwise=True)
            elif orientation == '7':
                image = image.Mirror(horizontally=True)
                image = image.Rotate90(clockwise=True)
            elif orientation == '8':
                image = image.Rotate90(clockwise=False)

        # scale the image, preserving the aspect ratio
        width = image.GetWidth()
        height = image.GetHeight()
        if width > height:
            height = self.__max_size * height / width
            width = self.__max_size
        else:
            width = self.__max_size * width / height
            height = self.__max_size
        image = image.Scale(width, height)

        self.__image.SetBitmap(wx.Bitmap(image))
        self.Refresh()
        self._sizer.Layout()

    def load_tagsets(self, origin, tagsets):
        """Set the text of the tagsets widget.

        Positional arguments:
        origin -- the origin ("local"|"global")
        tagsets -- dict returned by media.tagsets.Tagsets.get_tagsets()
        """
        text = ''

        for abbr, tags in tagsets.items():
            text += "{} {}\n".format(abbr, ','.join(tags))
        self._tagsets[origin].SetValue(text)

    def get_tagsets(self, origin):
        """Get the text of the tagset widget

        Positional arguments:
        origin -- the origin ("local"|"global")
        """
        return self._tagsets[origin].GetValue()

    def _format_rating_as_unicode(self, rating):
        """Format XMP:Rating (-1 [rejected], 0 - 5) as stars."""
        try:
            num = int(rating)
        except ValueError:
            logger.error('Invalid rating "{}" given'.format(rating))
            num = 0
        if num == -1:
            #return "\U0001F6AE" # "put litter in it's place" (looks weird)
            return "\U0001F5D1" # "wastebasket"
        elif -1 < num < 6:
            return (num * "\u2605").ljust(5, "\u2606")
        else:
            if not num == 0:
                logger.error('Invalid rating "{}" given'.format(rating))
            return (5 * "\u2606")

    def load_info(self, metadata):
        """Set the text of the info widget.

        Positional arguments:
        metadata -- dict of available metadata to display
        """
        text = ''
        text += str(metadata['index']) + '/' + str(metadata['n']) + "\n"
        text += metadata['name']
        text += (' (DELETED)' if metadata['deleted'] else '' ) + "\n"
        text += metadata['date'] + "\n"
        text += self._format_rating_as_unicode(metadata['rating']) #+ "\n"
        self.__info_panel.SetLabel(text)

    def load_metadata(self, metadata):
        """Set the text of the metadata widget.

        Positional arguments:
        metadata -- dict of available metadata to display
        """
        cfg = config.ConfigSingleton()
        tag_field = cfg.get('Metadata', 'field_tags', default=None)

        text = ''

        for key, value in metadata.items():
            # omit tags
            if key == tag_field:
                continue
            text += "{}: {}\n".format(key, value)
        self.__metadata_panel.SetValue(text)
        self.activate_source(metadata.get('FileName'))

    def load_tags(self, tags):
        """Set the text of the tags widget.

        Positional arguments:
        tags -- TagList to display
        """
        text = ''
        if not tags is None:
            tags = tags.get_tags()
            tags.sort()
            for tag in tags:
                text += "{}\n".format(tag)
        self.__metadata.SetValue(text)

    def load_sources(self, sources):
        """Display the different sources in a choice.

        Positional arguments:
        sources -- list of source filenames
        """
        self.__source_picker.Set(sources)

    def activate_source(self, source):
        """Set a source in the source choice.

        Positional arguments:
        sourec -- string filename
        """
        #if source is None:
        #    return
        self.__source_picker.SetSelection(
                self.__source_picker.FindString(source))

    def set_source_picker_action(self, on_change):
        """Bind a function to the wx.Choice."""
        if not on_change is None:
            self.Bind(wx.EVT_CHOICE, on_change)

    def focus_command_entry(self):
        """Set focus to the command entry."""
        self.__command_entry.focus()

    def set_command_processor(self, processor_function):
        """Set a function to process the command.

        See ui.UI.process_command for more detail.

        Positional arguments:
        processor_function -- function to process the command
        """
        self.__command_entry.set_command_processor(processor_function)

class CustomWidget(wx.Panel):
    """Base class for custom widgets."""

    def __init__(self, parent, layout=wx.VERTICAL, *args, **kwargs):
        """Initialise panel and instance variables and add a BoxSizer.

        The vertical BoxSizer is available via _main_sizer.

        Positional arguments:
        parent -- wx.Window that serves as parent
        """
        wx.Panel.__init__(self, parent=parent, *args, **kwargs)
        self._sizer = wx.BoxSizer(layout)
        self.SetSizer(self._sizer)

class CommandEntry(CustomWidget):
    def __init__(self, parent, *args, **kwargs):
        """Construct the widget.

        Positional arguments:
        parent -- wx.Window that serves as parent
        """
        super(CommandEntry, self).__init__(parent, *args, **kwargs)

        self.__input = wx.TextCtrl(parent=self, id=wx.ID_ANY)
        self._sizer.Add(self.__input, flag=wx.EXPAND, proportion=1)

        self.__input.Bind(wx.EVT_CHAR, self._process_command)

        self.__process_command = None

    def _process_command(self, event):
        """Check each character for a command.

        Positional arguments:
        event -- the event that was intercepted
        """
        # if no processor was given input is useless
        if self.__process_command is None:
            raise ValueError('No processor function set.')
            return

        # catch all unicode keys
        key = event.GetUnicodeKey()
        # if a secial key (e.g. F1, ...) is pressed
        # GetUnicodeKey return wx.WXK_NONE
        if key == wx.WXK_NONE:
            # so try the key code
            # key = event.GetKeyCode()
            event.Skip()
            return
        elif key == wx.WXK_RETURN:
            key = "\n"
        else:
            key = chr(key)

        if self.__process_command(self.__input.GetValue() + key):
            # command has been processed so we can clear the input
            self.reset()
            return
        else:
            # need more input
            event.Skip()
            return

    def reset(self):
        """Reset the entry."""
        self.__input.SetValue('')

    def focus(self):
        """Focus the input."""
        self.__input.SetFocus()

    def set_command_processor(self, processor_function):
        """Set a function to process the command.

        Positional arguments:
        processor_function -- function to process the command
        """
        self.__process_command = processor_function

