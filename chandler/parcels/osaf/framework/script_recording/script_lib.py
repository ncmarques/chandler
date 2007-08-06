#   Copyright (c) 2003-2007 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import wx
from osaf.framework.blocks.Block import Block
from application.Application import stringToId
from osaf.framework.attributeEditors.AETypeOverTextCtrl import AETypeOverTextCtrl
from application import schema

def ProcessEvent (theClass, properties, attributes):
    def NameToWidget (name):
        """
        Given a name, returns the corresponding widget.
        """
        sentTo = None
        if type (name) is str:
            if name == "MainFrame":
                sentTo = application.mainFrame
            elif name == "__FocusWindow__":
                sentTo = wx.Window_FindFocus()
            else:
                sentTo = Block.findBlockByName (name)
                if sentTo is not None:
                    sentTo = sentTo.widget
                    if isinstance (sentTo, wx.grid.Grid):
                        sentTo = sentTo.GetGridWindow()
                    elif isinstance (sentTo, AETypeOverTextCtrl):
                          firstChild = sentTo.GetChildren()[0]
                          if isinstance (firstChild, wx.TextCtrl):
                              sentTo = firstChild
                else:
                    sentTo = wx.FindWindowById (stringToId [name])
        else:
            assert type (name) is int
            sentTo = wx.FindWindowById (name)
        return sentTo

    application = wx.GetApp()

    sentToWidget = NameToWidget (properties ["sentTo"])
    
    assert (isinstance (sentToWidget, wx.Window) or
            isinstance (sentToWidget, wx.Menu) or
            isinstance (sentToWidget, wx.MenuItem) or
            isinstance (sentToWidget, wx.ToolBarTool))
    
    if isinstance (sentToWidget, wx.ToolBarTool):
        assert sentToWidget.IsControl()
        sentToWidget = sentToWidget.GetControl()
        # On platforms other than mac wx.SearchCtrl's child is the wx.TextCtrl
        # rather than the wx.SearchCtrl itself.
        if wx.Platform != "__WXMAC__":
            if isinstance (sentToWidget, wx.SearchCtrl):
                sentToWidget = sentToWidget.GetChildren()[0]

    elif isinstance (sentToWidget, wx.MenuItem):
        assert sentToWidget.IsSubMenu()
        sentToWidget = sentToWidget.GetSubMenu()

    eventType = properties["eventType"]

    if theClass is not wx.grid.GridEvent:
        event = theClass()
        for (attribute, value) in attributes.iteritems():
            setattr (event, attribute, value)
    else:
        # Unfortunately, wx.grid.GridEvent doesn't have setters and getters. Eventually
        # I will add this to wxWidgets and remove this special case code -- DJA
        position = attributes ["Position"]
        event = wx.grid.GridEvent (-1,
                                   eventType.evtType[0],
                                   Block.findBlockByName (properties ["sentTo"]).widget,
                                   row = attributes ["Row"],
                                   col = attributes ["Col"],
                                   x = position [0], y = position [1])

    event.SetEventObject (sentToWidget)
    event.SetEventType (eventType.evtType[0])

    # Use the associated window if present to set the Id of the event
    associatedBlock = properties.get ("associatedBlock", None)
    if associatedBlock is not None:
        event.SetId (Block.findBlockByName (associatedBlock).widget.GetId())

    newFocusWindow = properties.get ("newFocusWindow", None)
    if newFocusWindow != None:
        ProcessEvent.newFocusWindow = newFocusWindow
        ProcessEvent.newFocusWindowClass = properties["newFocusWindowClass"]
            
    # Special case clicks on checkboxes to toggle the widget's value
    # And special case wx,Choice to set the selection. Both of these
    # are necessary before the event is processed so the GetValue
    # validation passes
    if eventType is wx.EVT_CHECKBOX:
        sentToWidget.SetValue (not sentToWidget.GetValue())

    # andSpecial case wx,Choice to set the selection
    elif eventType is wx.EVT_CHOICE:
        sentToWidget.SetSelection (properties ["selectedItem"])

    # A bug in wxWidgets on Windows stores the wrong value for m_rawCode in wx.EVT_CHAR
    # Since the correct valus is stored in wx.EVT_KEY_DOWN and wx.EVT_KEY_DOWN
    # precedes wx.EVT_KEY_DOWN, we'll cache it for the next wx.EVT_KEY_DOWN
    # Raw key codes are only used on Windows. There they correspond to virtual
    # keycodes. For this reason we record scripts on Windows to play back on the
    # other platforms.
    if eventType is wx.EVT_KEY_DOWN:
        ProcessEvent.last_rawCode = event.m_rawCode

    # Verify script if necessary
    if schema.ns('osaf.framework.script_recording', application.UIRepositoryView).RecordingController.verifyScripts:
        # Make sure the menu or button is enabled
        if eventType is wx.EVT_MENU:
            updateUIEvent = wx.UpdateUIEvent (event.GetId())
            updateUIEvent.SetEventObject (sentToWidget)
            sentToWidget.ProcessEvent (updateUIEvent)
            assert updateUIEvent.GetEnabled() is True, "You're sending a command to a disable menu"
            
        # Check to makee sure we're focused to the right window
        newFocusWindow = ProcessEvent.newFocusWindow
        if newFocusWindow is not None:
            focusWindow = wx.Window_FindFocus()
            
            if wx.Platform != "__WXMAC__" and focusWindow is not None:
                # On platforms other than mac the focus window is a wx.TextCtrl
                # whose parent is the wx.SearchCtrl. Go dig out the toolbar item
                # corresponding to the wx.SearchCtrl.
                parentWidget = focusWindow.GetParent()
                if isinstance (parentWidget, wx.SearchCtrl):
                    focusWindow = parentWidget

            # Rarely, a block has more than one widget associated with it, e.g. a toolBarItem
            # with a wx.SearchCtrl. If we get the widget associated with out block, we'll always
            # get the same widget in the case is case of multiple widgets per block.s
            if hasattr (focusWindow, "blockItem"):
                focusWindow = focusWindow.blockItem.widget

            # On Macintosh there is a setting under SystemPreferences>Keyboar&Mouse>KeyboardShortcuts
            # neare the bottom of the page titled "Full Keyboard Access" that defaults to
            # not letting you set the focus to certain controls, e.g. CheckBoxes. So we
            # don't verify the focus in those cases.
            #
            # On Linux events sent to toolbar cause the focus window to become None
            if not ( (wx.Platform == "__WXMAC__" and issubclass (ProcessEvent.newFocusWindowClass, wx.CheckBox)) or
                     (wx.Platform == "__WXGTK__" and isinstance (sentToWidget, wx.ToolBar)) ):
                if type (newFocusWindow) is str:
                    assert focusWindow is NameToWidget (newFocusWindow), "An unexpected window has the focus"
                else:
                    assert isinstance (focusWindow, ProcessEvent.newFocusWindowClass), (
                           "The focus window, " + str(focusWindow) +
                           ", is not class " + str (ProcessEvent.newFocusWindowClass) +
                           ". Parent window is " +  str (focusWindow.GetParent()) )
                    if newFocusWindow > 0:
                        assert focusWindow.GetId() == newFocusWindow, "Focus window has unexpected id"
                    else:
                        assert focusWindow.GetId() < 0, "Focus window has unexpected id"
    
        # Check to make sure last event caused expected change

        lastSentToWidget = ProcessEvent.lastSentToWidget
        if lastSentToWidget is not None and not isinstance (lastSentToWidget, wx._core._wxPyDeadObject):
            GetValueMethod = getattr (lastSentToWidget, "GetValue", None)
        else:
            GetValueMethod = None

        assert properties.has_key ("lastWidgetValue") == (GetValueMethod is not None), "widget's value existance doesn't match existance when the script was recorded"

        if GetValueMethod is not None:
            value = GetValueMethod()
            lastWidgetValue = properties ["lastWidgetValue"]
            # Special hackery for string that varies depending on Chandler build
            if type (value) is unicode and value.startswith (u"Welcome to Chandler 0.7.dev-r"):
                assert lastWidgetValue.startswith (u"Welcome to Chandler 0.7.dev-r")
            else:
                 assert value == lastWidgetValue, (
                        "widget's value, \"" + str(value) +
                        "\", doesn't match the value when the script was recorded: \"" + str (lastWidgetValue) + '"' )

        # Keep track of the last widget. Use Id because widget can be deleted
        ProcessEvent.lastSentToWidget = sentToWidget

    if not sentToWidget.ProcessEvent (event):
        if (eventType is wx.EVT_KEY_DOWN and
            event.m_keyCode in set ((wx.WXK_ESCAPE, wx.WXK_TAB, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER))):
            # Special case key downs that end edits in the grid
            gridWindow = sentToWidget.GetParent()
            if (gridWindow is not None and
                isinstance (gridWindow.GetParent(), wx.grid.Grid)):
                event.SetEventObject (gridWindow)
                gridWindow.ProcessEvent (event)

        elif eventType is wx.EVT_CHAR:
            # Make sure the selection is valid
            if __debug__:
                GetSelectionMethod = getattr (sentToWidget, "GetSelection", None)
                if GetSelectionMethod is not None:
                    (start, end) = GetSelectionMethod()
                    assert start >= 0 and end >= 0 and start <= end

            # Try EmulateKeyPress
            EmulateKeyPress = getattr(sentToWidget, 'EmulateKeyPress', None)
            if EmulateKeyPress is not None:
                # A bug in wxWidgets on Windows stores the wrong value for m_rawCode in wx.EVT_CHAR
                # Since the correct valus is stored in wx.EVT_KEY_DOWN and wx.EVT_KEY_DOWN
                # precedes wx.EVT_KEY_DOWN, we'll cache it for the next wx.EVT_KEY_DOWN
                event.m_rawCode = ProcessEvent.last_rawCode
                EmulateKeyPress (event)

        # Left down changes the focus
        elif eventType is wx.EVT_LEFT_DOWN:
            sentToWidget.SetFocus()

    selectionRange = properties.get ("selectionRange", None)
    if selectionRange is not None:
        (start, end) = selectionRange
        sentToWidget.SetSelection (start, end)

    # On windows when we propagate notifications while editing a text control
    # it will end up calling wxSynchronizeWidget in wxTable, which will end the
    # editing of the table
    if not isinstance (sentToWidget, wx.TextCtrl):
        application.propagateAsynchronousNotifications()

    application.Yield (True)
    
    # Since scrips don't actually move the cursor and cause wxMouseCaptureLostEvents
    # to be generated we'll periodically release the capture from all the windows.
    # Alternatively, it might be better to record and playback wxMouseCaptureLostEvents.
    while True:
        capturedWindow = wx.Window.GetCapture()
        if capturedWindow is not None:
            capturedWindow.ReleaseMouse()
        else:
            break
    
def InitializeScript ():
    ProcessEvent.lastSentToWidget = None
    ProcessEvent.newFocusWindow = None
