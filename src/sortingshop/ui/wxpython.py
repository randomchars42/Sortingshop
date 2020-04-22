#!/usr/bin/env python3

import logging
from pathlib import Path
import wx
import pkg_resources

from . import ui

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

    def construct(self):
        """Construct the frame and its layout."""
        # the application frame (what you see as a "window")
        self.__frame = wx.Frame(parent=None, id=wx.ID_ANY, title='Sortingshop')
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
        homepage.bind_to_button('tag', lambda event: self._display_page('tag'))

        # the page used to tag individual media files
        tag_page = TagPage(panel, layout=wx.HORIZONTAL,
                callback_on_back=self._display_previous_page)
        sizer.Add(tag_page, flag=wx.EXPAND, proportion=1)
        self.__pages['tag'] = tag_page
        tag_page.set_command_processor(self.process_command)

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

    def display_tagsets(self, tagsets):
        raise NotImplementedError('method "display_tagsets" not implemented')
        pass

    def display_shortcuts(self, shortcuts):
        raise NotImplementedError('method "display_shortcuts" not implemented')
        pass

    def display_picture(self, picture_path):
        """Display the given picture.

        Positional arguments:
        picture_path -- path to the picture (string / Path)
        """
        self.__pages['tag'].load_image(str(picture_path))

    def display_sources(self, sources):
        raise NotImplementedError('method "display_sources" not implemented')
        pass

    def display_metadata(self, metadata):
        raise NotImplementedError('method "display_metadata" not implemented')
        pass

    def display_message(self, message):
        raise NotImplementedError('method "display_message" not implemented')
        pass

    def display_dialog(self, message, dialog_type="yesno"):
        raise NotImplementedError('method "display_message" not implemented')
        pass

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

        self.__buttons = {}

        if not callback_on_back is None:
            button_back = wx.Button(parent=self, label='Back')
            button_back.Bind(event=wx.EVT_BUTTON, handler=callback_on_back)
            self.__bar_sizer.Add(button_back, flag=wx.ALIGN_RIGHT)
            self.__buttons['back'] = button_back

    def show_page(self):
        """Extensible wrapper around window.Show."""
        self.Show()

    def hide_page(self):
        """Extensible wrapper around window.Hide."""
        self.Hide()

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

        self.__buttons = {}

        self.__buttons['tag'] = wx.Button(parent=self, label='Tag')
        self._sizer.Add(self.__buttons['tag'], flag=wx.ALIGN_CENTER|wx.EXPAND)

        # center buttons vertically
        self._sizer.AddStretchSpacer(prop=1)

    def bind_to_button(self, button, callback):
        """Bind a callback to a button on this page.

        Positional arguments:
        button -- the name of the button (string)
        callback -- function to call
        """
        if not button in self.__buttons:
            raise ValueError('No such button ("{}")'.format(button))
        self.__buttons[button].Bind(event=wx.EVT_BUTTON, handler=callback)

class TagPage(Page):
    def __init__(self, parent, *args, **kwargs):
        """Construct the page and initiate instance variables.

        Positional arguments:
        parent -- wx.Window that serves as parent
        """
        super(TagPage, self).__init__(parent, *args, **kwargs)

        # the max height and width
        self.__max_size = 400

        # construct

        # two columns
        self.__column_1 = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self.__column_1, flag=wx.EXPAND, proportion=2)
        self.__column_2 = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self.__column_2, flag=wx.EXPAND, proportion=1)

        # image
        # placeholder where we will load the image into
        image = wx.Image(self.__max_size, self.__max_size)
        self.__image = wx.StaticBitmap(self, id=wx.ID_ANY,
                bitmap=wx.Bitmap(image))
        self.__column_1.Add(self.__image, flag=wx.CENTER)

        # command entry
        self.__command_entry = CommandEntry(parent=self)
        self.__column_1.Add(self.__command_entry, flag=wx.EXPAND, proportion=1)



        # tagsets
        self.__tagsets = wx.TextCtrl(self, id=wx.ID_ANY,
                style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.__column_2.Add(self.__tagsets, flag=wx.EXPAND, proportion=1)

        # finished construction

        # load a default image
        self.load_image(pkg_resources.resource_filename(__name__,
            'resources/default.jpeg'))

    def show_page(self):
        """Show the page and focus the CommandEntry."""
        super(TagPage, self).show_page()
        self.focus_command_entry()

    def load_image(self, path):
        """Load the image, scale it down and display it.

        Positional arguments:
        path -- path of the image (string or Path)
        """
        image = wx.Image(str(path), type=wx.BITMAP_TYPE_ANY)
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

    def load_tagsets(self, tagsets):
        """Set the text of the tagsets widget.

        Positional arguments:
        tagsets -- the tagsets to display
        """
        self.__tagsets.SetValue(tagsets)

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
            #event.Skip()
            return

        # catch all unicode keys
        key = event.GetUnicodeKey()
        # if a secial key (e.g. F1, ...) is pressed
        # GetUnicodeKey return wx.WXK_NONE
        if key == wx.WXK_NONE:
            # so try the key code
            # key = event.GetKeyCode()
            # swallow the event and ignore
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
