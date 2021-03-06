#! /usr/bin/env python
#   Copyright (c) 2006-2007 Open Source Applications Foundation
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


import os, sys
from optparse import OptionParser
from build_lib import getCommand
from poUtility import parse, checkPrintValues

class LocalizationBase(object):
    CHANDLERBIN = None
    CHANDLERHOME = None
    BINROOT = None
    PYTHON = None
    CONFIGITEMS = None
    OPTIONS = None
    RAISED = False
    DESC = ""

    CHANDLER = ["application", os.path.join("parcels", "osaf")]

    def __init__(self):
        isWindows = self.getPlatform() == 'Windows'

        if os.environ.has_key("CHANDLERHOME"):
            self.CHANDLERHOME = os.environ["CHANDLERHOME"]
        else:
            self.CHANDLERHOME = os.getcwd()

        try:
            if not "Chandler.py" in os.listdir(self.CHANDLERHOME):
                raise Exception()
        except:
            self.raiseError("CHANDLERHOME is invalid '%s'." % self.CHANDLERHOME)

        if os.environ.has_key("CHANDLERBIN"):
            self.CHANDLERBIN = os.environ["CHANDLERBIN"]
        else:
            self.CHANDLERBIN = self.CHANDLERHOME

        if isWindows and sys.platform == 'cygwin':
            self.CHANDLERHOME = getCommand(['cygpath', '-a', self.CHANDLERHOME])
            self.CHANDLERBIN  = getCommand(['cygpath', '-a', self.CHANDLERBIN])

        if isWindows:
            pyScript = 'RunPython.bat'
        else:
            pyScript = 'RunPython'

        try:
            if "release" in os.listdir(self.CHANDLERBIN) and os.path.exists(os.path.join(self.CHANDLERBIN, "release", pyScript)):
                self.BINROOT = os.path.join(self.CHANDLERBIN, "release")

            elif "debug" in os.listdir(self.CHANDLERBIN) and os.path.exists(os.path.join(self.CHANDLERBIN, "debug", pyScript)):
                self.BINROOT = os.path.join(self.CHANDLERBIN, "debug")

            else:
                self.raiseError("No debug or release directory under CHANDLERBIN.")
        except:
            self.raiseError("CHANDLERBIN is invalid '%s'." % self.CHANDLERBIN)

        self.PYTHON = os.path.join(self.BINROOT, pyScript)

    def checkPOFile(self, poFileName):
        try:
            poFile = parse(poFileName)

            msgidResults = checkPrintValues(poFile)

            if len(msgidResults):
                resultsStr = "    WARNING: Only dictionary replaceable values\n" \
                             "             are allowed in localizable strings.\n\n"

            else:
                resultsStr = ""

            for poEntry, values in msgidResults:
                resultsStr += "    invalid value%s '%s' found at %s\n" % \
                              (len(values) > 1 and 's' or '', ", ".join(values),
                               ", ".join(poEntry.sourceFiles))

            if len(resultsStr):
                return resultsStr

            return None

        except Exception, e:
            return str(e)


    def debug(self):
        print "\n\nProgram run with the following configuration:"
        print "_______________________________________________\n"
        print "CHANDLERHOME: ", self.CHANDLERHOME
        print "CHANDLERBIN: ", self.CHANDLERBIN
        print "BINROOT: ", self.BINROOT
        print "PYTHON: ", self.PYTHON
        print "OPTIONS: ", self.OPTIONS



    def raiseError(self, txt, banner=True):
        if self.RAISED:
            return

        self.RAISED = True

        if banner:
            print "\n\nThe following error was raised: "
            print "----------------------------------------\n%s\n\n" % txt
        else:
            print txt

        #XXX For some reason this raises an Exception when
        #    called on Linux
        sys.exit(-1)
        
    

    def getPlatform(self):
        if sys.platform == 'darwin':
            return "Mac"

        if sys.platform == 'cygwin' or os.name == 'nt':
            return "Windows"

        return "Linux"


    def getOpts(self):
        self.CONFIGITEMS['Debug'] = ('', '--debug', False, \
                                  'Prints debugging information to the stdout')

        # %prog expands to os.path.basename(sys.argv[0])
        usage  = "usage: %prog [options]"
        parser = OptionParser(usage=usage, version="%prog 1.0")
        parser.set_description(self.DESC)

        for key in self.CONFIGITEMS:
            (shortCmd, longCmd, argReq, helpText) = self.CONFIGITEMS[key]

            if argReq:
                parser.add_option(shortCmd, longCmd, dest=key, help=helpText)
            else:
                parser.add_option(shortCmd, longCmd, dest=key, action="store_true",  help=helpText)

        (self.OPTIONS, args) = parser.parse_args()


    def findFile(self, fileName):
        dir = os.listdir(os.getcwd())

        if fileName in dir:
            return os.path.join(os.getcwd(), fileName)

        dir = os.listdir(self.CHANDLERHOME)

        if fileName in dir:
            return os.path.join(self.CHANDLERHOME, fileName)

        return None


    def findPath(self, name):
        fullPath = os.path.join(os.getcwd(), name)
        #This will fail if name not a relative path
        if os.access(fullPath, os.F_OK):
            return fullPath

        #is it a full path?
        if os.access(name, os.F_OK):
            return name

        return None

