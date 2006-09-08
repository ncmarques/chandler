# This file was automatically generated by pywxrc, do not edit by hand.
# -*- coding: UTF-8 -*-

# Unfortunately HAVE to edit because of res.Load path issue

#   Copyright (c) 2006 Open Source Applications Foundation
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
import wx.xrc as xrc

__res = None

def get_resources():
    """ This function provides access to the XML resources in this module."""
    global __res
    if __res == None:
        __init_resources()
    return __res


class xrcFRAME(wx.Frame):
    def PreCreate(self, pre):
        """ This function is called during the class's initialization.
        
        Override it for custom setup before the window is created usually to
        set additional window styles using SetWindowStyle() and SetExtraStyle()."""
        pass

    def __init__(self, parent):
        # Two stage creation (see http://wiki.wxpython.org/index.cgi/TwoStageCreation)
        pre = wx.PreFrame()
        self.PreCreate(pre)
        get_resources().LoadOnFrame(pre, parent, "FRAME")
        self.PostCreate(pre)

        # Define variables for the controls
        self.panel = xrc.XRCCTRL(self, "panel")
        self.disableFeedback = xrc.XRCCTRL(self, "disableFeedback")
        self.requiredPage = xrc.XRCCTRL(self, "requiredPage")
        self.text = xrc.XRCCTRL(self, "text")
        self.optionalPage = xrc.XRCCTRL(self, "optionalPage")
        self.email = xrc.XRCCTRL(self, "email")
        self.comments = xrc.XRCCTRL(self, "comments")
        self.delButton = xrc.XRCCTRL(self, "delButton")
        self.sysInfo = xrc.XRCCTRL(self, "sysInfo")
        self.sendButton = xrc.XRCCTRL(self, "sendButton")
        self.restartButton = xrc.XRCCTRL(self, "restartButton")
        self.closeButton = xrc.XRCCTRL(self, "closeButton")



# ------------------------ Resource data ----------------------

def __init_resources():
    global __res
    __res = xrc.EmptyXmlResource()

    # Have to edit the path to the xrc file
    import os, sys
    xrcFile = os.path.join(os.path.dirname(__file__), 'feedback.xrc')
    xrcFile = unicode(xrcFile, sys.getfilesystemencoding())
    __res.Load(xrcFile)
