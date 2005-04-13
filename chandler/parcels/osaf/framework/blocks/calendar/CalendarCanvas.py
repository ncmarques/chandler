""" Canvas for calendaring blocks
"""

__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import wx
import wx.colheader
import mx.DateTime as DateTime

import osaf.contentmodel.calendar.Calendar as Calendar

import osaf.framework.blocks.DragAndDrop as DragAndDrop
import osaf.framework.blocks.Block as Block
import osaf.framework.blocks.calendar.CollectionCanvas as CollectionCanvas

class CalendarCanvasItem(CollectionCanvas.CanvasItem):
    """
    Base class for calendar items. Covers:
    - editor position & size
    - text wrapping
    - conflict management
    """
    
    def __init__(self, *args, **keywords):
        super(CalendarCanvasItem, self).__init__(*args, **keywords)
        self._parentConflicts = []
        self._childConflicts = []
        # the rating of conflicts - i.e. how far to indent this
        self._conflictDepth = 0
                
        # the total depth of all conflicts - i.e. the maximum simultaneous 
        # conflicts with this item, including this one
        self._totalConflictDepth = 1
        
    def GetEditorPosition(self):
        """
        This returns a location to show the editor. By default it is the same
        as the default bounding box
        """
        return self._bounds.GetPosition()
        
    def GetDragOrigin(self):
        """
        This is just a stable coordinate that we can use so that when dragging
        items around, for example you can use this to know consistently where 
        the mouse started relative to this origin
        """
        return self._bounds.GetPosition()
        
    def GetMaxEditorSize(self):
        return self._bounds.GetSize()
    
    def GetStatusPen(self):
        item = self.GetItem()
        if (item.transparency == "confirmed"):
            pen = wx.Pen(wx.BLACK, 3)
        elif (item.transparency == "fyi"):
            pen = wx.Pen(wx.LIGHT_GREY, 3)
        elif (item.transparency == "tentative"):
            pen = wx.Pen(wx.BLACK, 3, wx.DOT)
        return pen
        
    # Drawing utility -- scaffolding, we'll try using editor/renderers
    def DrawWrappedText(self, dc, text, rect):
        # Simple wordwrap, next step is to not overdraw the rect
        
        result = []
        
        lines = text.splitlines()
        y = rect.y
        for line in lines:
            x = rect.x
            wrap = 0
            for word in line.split():
                width, height = dc.GetTextExtent(word)

                # first see if we want to jump to the next line
                # (careful not to jump if we're already at the beginning of the line)
                if (x != rect.x and x + width > rect.x + rect.width):
                    y += height
                    x = rect.x
                
                # if we're out of vertical space, just return
                if (y + height > rect.y + rect.height):
                    return y
                   
                # if we wrapped but we still can't fit the word,
                # just truncate it    
                if (x == rect.x and width > rect.width):
                    self.DrawClippedText(dc, word, x, y, rect.width)
                    y += height
                    continue
                
                dc.DrawText(word, x, y)
                x += width
                width, height = dc.GetTextExtent(' ')
                dc.DrawText(' ', x, y)
                x += width
            y += height
        return y

    def DrawClippedText(self, dc, word, x, y, maxWidth):
        # keep shortening the word until it fits
        for i in xrange(len(word), 0, -1):
            smallWord = word[0:i] # + "..."
            width, height = dc.GetTextExtent(smallWord)
            if width <= maxWidth:
                dc.DrawText(smallWord, x, y)
                return
                
    def AddConflict(self, child):
        # we might want to keep track of the inverse conflict as well,
        # for conflict bars
        child._parentConflicts.append(self)
        self._childConflicts.append(child)
        
    def FindFirstGapInSequence(self, seq):
        """
        Look for the first gap in a sequence - for instance
         0,2,3: choose 1
         1,2,3: choose 0
         0,1,2: choose 3        
        """
        for index, value in enumerate(seq):
            if index != value:
                return index
                
        # didn't find any gaps, so just put it one higher
        return index+1
        
    def CalculateConflictDepth(self):
        if not self._parentConflicts:
            return 0
        
        # We'll find out the depth of all our parents, and then
        # see if there's an empty gap we can fill
        # this relies on parentDepths being sorted, which 
        # is true because the conflicts are added in 
        # the same order as the they appear in the calendar
        parentDepths = [parent._conflictDepth for parent in self._parentConflicts]
        self._conflictDepth = self.FindFirstGapInSequence(parentDepths)
        return self._conflictDepth
        
    def GetIndentLevel(self):
        # this isn't right. but its a start
        # it should be some wierd combination of 
        # maximum indent level of all children + 1
        return self._conflictDepth
        
    def GetMaxDepth(self):
        maxparents = maxchildren = 0
        if self._childConflicts:
            maxchildren = max([child.GetIndentLevel() for child in self._childConflicts])
        if self._parentConflicts:
            maxparents = max([parent.GetIndentLevel() for parent in self._parentConflicts])
        return max(self.GetIndentLevel(), maxchildren, maxparents)
        

class ColumnarCanvasItem(CalendarCanvasItem):
    resizeBufferSize = 5
    textMargin = 3
    RESIZE_MODE_START = 1
    RESIZE_MODE_END = 2
    def __init__(self, item, calendarCanvas, *arguments, **keywords):
        super(ColumnarCanvasItem, self).__init__(None, item)
        
        # this is really annoying that we need to keep a reference back to 
        # the calendar canvas in every single ColumnarCanvasItem, but we
        # need it for drawing hints.. is there a better way?
        self._calendarCanvas = calendarCanvas

    def UpdateDrawingRects(self):
        item = self.GetItem()
        indent = self.GetIndentLevel() * 5
        width = self.GetMaxDepth() * 5
        self._boundsRects = list(self.GenerateBoundsRects(self._calendarCanvas,
                                                          item.startTime,
                                                          item.endTime, indent, width))
        self._bounds = self._boundsRects[0]

        r = self._boundsRects[-1]
        self._resizeLowBounds = wx.Rect(r.x, r.y + r.height - self.resizeBufferSize,
                                        r.width, self.resizeBufferSize)
        
        r = self._boundsRects[0]
        self._resizeTopBounds = wx.Rect(r.x, r.y,
                                        r.width, self.resizeBufferSize)
        

    def isHitResize(self, point):
        """ Hit testing of a resize region.
        
        @param point: point in unscrolled coordinates
        @type point: wx.Point
        @return: True if the point hit the resize region
        @rtype: Boolean
        """
        return (self._resizeTopBounds.Inside(point) or
                self._resizeLowBounds.Inside(point))

    def isHit(self, point):
        """
        User may have clicked in any of the possible bounds
        """
        for rect in self._boundsRects:
            if rect.Inside(point):
                return True
        return False

    def getResizeMode(self, point):
        """ Returns the mode of the resize, either RESIZE_MODE_START or
        RESIZE_MODE_END.

        The resize mode is RESIZE_MODE_START if dragging from the top of the event,
        and RESIZE_MODE_END if dragging from the bottom of the event. None indicates
        that we are not resizing at all.

        @param point: drag start position in uscrolled coordinates
        @type point: wx.Point
        @return: resize mode, RESIZE_MODE_START, RESIZE_MODE_END or None
        @rtype: string or None
        """
        
        if hasattr(self, '_forceResizeMode'):
            return self._forceResizeMode
            
        if self._resizeTopBounds.Inside(point):
            return self.RESIZE_MODE_START
        if self._resizeLowBounds.Inside(point):
            return self.RESIZE_MODE_END
        return None
        
    def SetResizeMode(self, mode):
        self._forceResizeMode = mode
        
    def ResetResizeMode(self):
        if hasattr(self, '_forceResizeMode'):
            del self._forceResizeMode
    
    def GenerateBoundsRects(calendarCanvas, startTime, endTime, indent=0, width=0):
        """
        Generate a bounds rectangle for each day period. For example, an event
        that goes from noon monday to noon wednesday would have three bounds rectangles:
            one from noon monday to midnight
            one for all day tuesday
            one from midnight wednesday morning to noon wednesday
        """
        # calculate how many unique days this appears on 
        days = int(endTime.absdays) - int(startTime.absdays) + 1
        
        for i in xrange(days):
            
            # first calculate the midnight time for the beginning and end
            # of the current day
            absDay = int(startTime.absdays) + i
            absDayStart = DateTime.DateTimeFromAbsDays(absDay)
            absDayEnd = DateTime.DateTimeFromAbsDays(absDay + 1)
            
            boundsStartTime = max(startTime, absDayStart)
            boundsEndTime = min(endTime, absDayEnd)
            
            rect = ColumnarCanvasItem.MakeRectForRange(calendarCanvas, boundsStartTime, boundsEndTime)
            rect.x += indent
            rect.width -= width
            try:
                yield rect
            except ValueError:
                pass

    GenerateBoundsRects = staticmethod(GenerateBoundsRects)
        
    def MakeRectForRange(calendarCanvas, startTime, endTime):
        """
        Turn a datetime range into a rectangle that can be drawn on the screen
        This is a static method, and can be used outside this class
        """
        startPosition = calendarCanvas.getPositionFromDateTime(startTime)
        
        # ultimately, I'm not sure that we should be asking the calendarCanvas
        # directly for dayWidth and hourHeight, we probably need some system 
        # instead similar to getPositionFromDateTime where we pass in a duration
        duration = (endTime - startTime).hours
        (cellWidth, cellHeight) = (calendarCanvas.dayWidth, int(duration * calendarCanvas.hourHeight))
        
        # Now handle indentation based on conflicts -
        # we really need a way to proportionally size
        # items, so that the right side of the rectangle
        # shrinks as well
        return wx.Rect(startPosition.x, startPosition.y, cellWidth, cellHeight)

    MakeRectForRange = staticmethod(MakeRectForRange)

    def Draw(self, dc, boundingRect, brushContainer):
        item = self._item

        time = item.startTime

        # Draw one event - an event consists of one or more bounds
        lastRect = len(self._boundsRects) - 1
            
        clipRect = None   
        (cx,cy,cwidth,cheight) = dc.GetClippingBox()
        if not cwidth == cheight == 0:
            clipRect = wx.Rect(x,y,width,height)
            
        for rectIndex, itemRect in enumerate(self._boundsRects):        
            
            dc.SetPen(brushContainer.selectionPen)

            # properly round the corners - first 
            # and last boundsRect gets some rounding, and they
            # may actually be the same boundsRect
            hasTopRightRounded = hasBottomRightRounded = False
            drawTime = False
            if rectIndex == 0:
                hasTopRightRounded = True
                drawTime = True
            if rectIndex == lastRect:
                hasBottomRightRounded = True

            self.DrawDRectangle(dc, itemRect, hasTopRightRounded, hasBottomRightRounded)

            pen = self.GetStatusPen()
    
            cornerRadius = 0
            pen.SetCap(wx.CAP_BUTT)
            dc.SetPen(pen)
            dc.DrawLine(itemRect.x + 2, itemRect.y + (cornerRadius*3/4),
                        itemRect.x + 2, itemRect.y + itemRect.height - (cornerRadius*3/4))
    
            # Shift text
            x = itemRect.x + self.textMargin + 5
            y = itemRect.y + self.textMargin
            width = itemRect.width - (self.textMargin + 10)
            height = 15
            timeRect = wx.Rect(x, y, width, height)
            
            # only draw date/time on first item
            if drawTime:
                # amazingly, there is no hour-without-the-zero in mx.DateTime!
                # (If anyone knows a better way to do this, please fix..)
                hour = str(int(time.Format('%I')))
                timeString = hour + time.Format(':%M %p').lower()
                te = dc.GetFullTextExtent(timeString, brushContainer.smallBoldFont)
                timeHeight = te[1]
                
                # draw the time if there is room
                if (timeHeight < itemRect.height/2):
                    dc.SetFont(brushContainer.smallBoldFont)
                    y = self.DrawWrappedText(dc, timeString, timeRect)
                
                textRect = wx.Rect(x, y, width, itemRect.height - (y - itemRect.y))
                
                dc.SetFont(brushContainer.smallFont)
                self.DrawWrappedText(dc, item.displayName, textRect)
        
        dc.DestroyClippingRegion()
        if clipRect:
            dc.SetClippingRect(clipRect)

    def DrawDRectangle(self, dc, rect, hasTopRightRounded=True, hasBottomRightRounded=True):
        """
        Make a D-shaped rectangle, optionally specifying if the top and bottom
        right side of the rectangle should have rounded corners. Uses
        clip rect tricks to make sure it is drawn correctly
        
        Side effect: Destroys the clipping region.
        """

        radius = 10
        diameter = radius * 2

        dc.DestroyClippingRegion()
        dc.SetClippingRect(rect)
        
        roundRect = wx.Rect(rect.x, rect.y, rect.width, rect.height)
        
        # first widen the whole thing left, this makes sure the 
        # left rounded corners aren't drawn
        roundRect.x -= radius
        roundRect.width += radius
        
        # now optionally push the other rounded corners off the top or bottom
        if not hasBottomRightRounded:
            roundRect.height += radius
            
        if not hasTopRightRounded:
            roundRect.y -= radius
            roundRect.height += radius
        
        # finally draw the clipped rounded rect
        dc.DrawRoundedRectangleRect(roundRect, radius)
        
        # draw the lefthand side border, to stay consistent all
        # the way around the rectangle
        dc.DrawLine(rect.x, rect.y, rect.x, rect.y + rect.height)

class HeaderCanvasItem(CalendarCanvasItem):
    def Draw(self, dc, brushContainer):
        item = self._item
        itemRect = self._bounds
                
        # draw little rectangle to the left of the item
        pen = self.GetStatusPen()
        
        pen.SetCap(wx.CAP_BUTT)
        dc.SetPen(pen)
        dc.DrawLine(itemRect.x + 2, itemRect.y + 3,
                    itemRect.x + 2, itemRect.y + itemRect.height - 3)
        
        # Shift text
        itemRect.x = itemRect.x + 6
        itemRect.width = itemRect.width - 6
        self.DrawWrappedText(dc, item.displayName, itemRect)

# hacky - might not work, but we don't even have a month canvas working right now
class MonthCanvasItem(CalendarCanvasItem):
    def Draw(self, dc, isSelected):
        if (self.blockItem.selection is item):
            dc.SetPen(wx.BLACK_PEN)
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.DrawRectangleRect(itemRect)
            
        self.DrawWrappedText(dc, self.GetItem().displayName, itemRect)
        

class CalendarEventHandler(object):

    """ Mixin to a widget class """

    def OnPrev(self, event):
        self.blockItem.decrementRange()
        self.blockItem.postDateChanged()
        self.wxSynchronizeWidget()

    def OnNext(self, event):
        self.blockItem.incrementRange()
        self.blockItem.postDateChanged()
        self.wxSynchronizeWidget()

    def OnToday(self, event):
        today = DateTime.today()
        self.blockItem.setRange(today)
        self.blockItem.postDateChanged()
        self.wxSynchronizeWidget()

class ClosureTimer(wx.Timer):
    """
    Helper class because targets may need to recieve multiple different timers
    """
    def __init__(self, callback, *args, **kwargs):
        super(ClosureTimer, self).__init__(*args, **kwargs)
        self._callback = callback
        
    def Notify(self):
        self._callback()

class CalendarBlock(CollectionCanvas.CollectionBlock):
    """ Abstract block used as base Kind for Calendar related blocks.

    This base class can be used for any block that displays a collection of
    items based on a date range.

    @ivar rangeStart: beginning of the currently displayed range (persistent)
    @type rangeStart: mx.DateTime.DateTime
    @ivar rangeIncrement: increment used to find the next or prev block of time
    @type rangeIncrement: mx.DateTime.RelativeDateTime
    """
    
    def __init__(self, *arguments, **keywords):
        super(CalendarBlock, self).__init__(*arguments, **keywords)

    # Event handling
    
    def onSelectedDateChangedEvent(self, event):
        """
        Sets the selected date range and synchronizes the widget.

        @param event: event sent on selected date changed event
        @type event: osaf.framework.blocks.Block.BlockEvent
        @param event['start']: start of the newly selected date range
        @type event['start']: mx.DateTime.DateTime
        """
        self.setRange(event.arguments['start'])
        self.widget.wxSynchronizeWidget()

    def postDateChanged(self):
        """
        Convenience method for changing the selected date.
        """
        self.postEventByName ('SelectedDateChanged',{'start':self.selectedDate})

    # Managing the date range

    def setRange(self, date):
        """ Sets the range to include the given date.

        @param date: date to include
        @type date: mx.DateTime.DateTime
        """
        self.rangeStart = date
        self.selectedDate = self.rangeStart

    def incrementRange(self):
        """ Increments the calendar's current range """
        self.rangeStart += self.rangeIncrement
        if self.selectedDate:
            self.selectedDate += self.rangeIncrement

    def decrementRange(self):
        """ Decrements the calendar's current range """
        self.rangeStart -= self.rangeIncrement
        if self.selectedDate:
            self.selectedDate -= self.rangeIncrement

    # Get items from the collection

    def getDayItemsByDate(self, date):
        nextDate = date + DateTime.RelativeDateTime(days=1)
        for item in self.contents:
            try:
                anyTime = item.anyTime
            except AttributeError:
                anyTime = False
            try:
                allDay = item.allDay
            except AttributeError:
                allDay = False
            if (item.hasLocalAttributeValue('startTime') and
                (allDay or anyTime) and
                (item.startTime >= date) and
                (item.startTime < nextDate)):
                yield item

    def itemIsInRange(self, item, start, end):
        """
        Helpful utility to determine if an item is within a given range
        Assumes the item has a startTime and endTime attribute
        """
        # three possible cases where we're "in range"
        # 1) start time is within range
        # 2) end time is within range
        # 3) start time before range, end time after
        return (((item.startTime >= start) and
                 (item.startTime < end)) or 
                ((item.endTime >= start) and
                 (item.endTime < end)) or 
                ((item.startTime <= start) and
                 (item.endTime >= end)))

    def getItemsInRange(self, date, nextDate):
        """
        Convenience method to look for the items in the block's contents
        that appear on the given date. We might be able to push this
        to Queries, but itemIsInRange is actually fairly complex.
        
        @type date: mx.DateTime.DateTime
        @type nextDate: mx.DateTime.DateTime
        @return: the items in this collection that appear within the given range
        @rtype: list of Items
        """
        for item in self.contents:
            try:
                anyTime = item.anyTime
            except AttributeError:
                anyTime = False
            try:
                allDay = item.allDay
            except AttributeError:
                allDay = False
            if (item.hasLocalAttributeValue('startTime') and
                item.hasLocalAttributeValue('endTime') and
                (not allDay and not anyTime) and
                self.itemIsInRange(item, date, nextDate)):
                yield item

    def GetCurrentDateRange(self):
        if self.dayMode:
            startDay = self.selectedDate
            endDay = startDay + DateTime.RelativeDateTime(days = 1)
        else:
            startDay = self.rangeStart
            endDay = startDay + self.rangeIncrement
        return (startDay, endDay)

                            

class wxCalendarCanvas(CollectionCanvas.wxCollectionCanvas):
    """
    Base class for all calendar canvases - handles basic item selection, 
    date ranges, and so forth
    """
    def __init__(self, *arguments, **keywords):
        super (wxCalendarCanvas, self).__init__ (*arguments, **keywords)

        self.majorLinePen = wx.Pen(wx.Colour(204, 204, 204))
        self.minorLinePen = wx.Pen(wx.Colour(229, 229, 229))
        self.selectionBrush = wx.Brush(wx.Colour(217, 217, 217)) # or 229?
        self.selectionPen = wx.Pen(wx.Colour(102, 102, 102)) # or 153?
        self.legendColor = wx.Colour(153, 153, 153)
        self.Bind(wx.EVT_SCROLLWIN, self.OnScroll)
        
    def OnInit(self):
        self.editor = wxInPlaceEditor(self, -1) 
        
    def OnScroll(self, event):
        self.Refresh()
        event.Skip()

    def OnSelectItem(self, item):
        self.parent.blockItem.selection = item
        self.parent.blockItem.postSelectItemBroadcast()
        self.parent.wxSynchronizeWidget()
    
    def GrabFocusHack(self):
        self.editor.SaveItem()
        self.editor.Hide()
        
    def GetCurrentDateRange(self):
        return self.parent.blockItem.GetCurrentDateRange()
    
class wxWeekPanel(wx.Panel, CalendarEventHandler):
    def __init__(self, *arguments, **keywords):
        super (wxWeekPanel, self).__init__ (*arguments, **keywords)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

        self.headerCanvas = wxWeekHeaderCanvas(self, -1)
        self.columnCanvas = wxWeekColumnCanvas(self, -1)
        self.headerCanvas.parent = self
        self.columnCanvas.parent = self

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.headerCanvas, 0, wx.EXPAND)
        box.Add(self.columnCanvas, 1, wx.EXPAND)
        self.SetSizer(box)

    def OnEraseBackground(self, event):
        pass

    def OnInit(self):
        self.headerCanvas.OnInit()
        self.columnCanvas.OnInit()

    def wxSynchronizeWidget(self):
        self.Layout()
        self.headerCanvas.wxSynchronizeWidget()
        self.columnCanvas.wxSynchronizeWidget()
        
    def PrintCanvas(self, dc):
        self.columnCanvas.PrintCanvas(dc)

    def OnDaySelect(self, day):
            
        startDate = self.blockItem.rangeStart
        selectedDate = startDate + DateTime.RelativeDateTime(days=day)
        
        # @@@ add method on block item for setting selected date
        self.blockItem.selectedDate = selectedDate
        self.blockItem.dayMode = True
        self.blockItem.postDateChanged()
        self.wxSynchronizeWidget()

    def OnWeekSelect(self):
        self.blockItem.dayMode = False
        self.blockItem.selectedDate = self.blockItem.rangeStart
        self.blockItem.postDateChanged()
        self.wxSynchronizeWidget()

    def OnExpand(self):
        self.headerCanvas.toggleSize()
        self.wxSynchronizeWidget()

class wxWeekHeaderCanvas(wxCalendarCanvas):
    def __init__(self, *arguments, **keywords):
        super (wxWeekHeaderCanvas, self).__init__ (*arguments, **keywords)

        self.fixed = True

        # @@@ constants
        
        self.hourHeight = 40
        self.scrollbarWidth = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)

    def OnInit(self):
        super (wxWeekHeaderCanvas, self).OnInit()

        # Set up sizers
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        navigationRow = wx.BoxSizer(wx.HORIZONTAL)
        labelRow = wx.BoxSizer(wx.HORIZONTAL)
        
        sizer.Add((3,3), 0, wx.EXPAND)
        sizer.Add(navigationRow, 0, wx.EXPAND)
        sizer.Add((3,3), 0, wx.EXPAND)
        sizer.Add(labelRow, 0, wx.EXPAND)
        sizer.Add((3,3), 0, wx.EXPAND)

        
        # 
        # top row - left/right buttons, anchored to the right
        self.prevButton = CollectionCanvas.CanvasBitmapButton(self, "application/images/backarrow.png")
        self.nextButton = CollectionCanvas.CanvasBitmapButton(self, "application/images/forwardarrow.png")
        self.Bind(wx.EVT_BUTTON, self.parent.OnPrev, self.prevButton)
        self.Bind(wx.EVT_BUTTON, self.parent.OnNext, self.nextButton)

        navigationRow.Add((0,0), 1, wx.EXPAND)
        navigationRow.Add(self.prevButton, 0, wx.EXPAND)
        navigationRow.Add((5,5), 0, wx.EXPAND)
        navigationRow.Add(self.nextButton, 0, wx.EXPAND)
        navigationRow.Add((5,5), 0, wx.EXPAND)
        
        # 
        # middle row - just the month label centered
        today = DateTime.today()
        self.monthButton = CollectionCanvas.CanvasTextButton(self, today.Format("%B %Y"),
                                                             self.bigFont, self.bigFontColor,
                                                             self.bgColor)
        labelRow.Add((0,0), 1)
        labelRow.Add(self.monthButton, 0, wx.ALIGN_CENTER)
        labelRow.Add((0,0), 1)

        #
        # finally the last row, with the header
        self.weekHeader = wx.colheader.ColumnHeader(self)
        
        # turn this off for now, because our sizing needs to be exact
        self.weekHeader.SetFlagProportionalResizing(False)
        self.weekHeaderHeight = self.weekHeader.GetSize().height
        headerLabels = ["Week", "S", "M", "T", "W", "T", "F", "S", "+"]
        for header in headerLabels:
            self.weekHeader.AppendItem(header, wx.colheader.COLUMNHEADER_JUST_Center, 5, bSortEnabled=False)
        self.Bind(wx.colheader.EVT_COLUMNHEADER_SELCHANGED, self.OnDayColumnSelect, self.weekHeader)

        sizer.Add(self.weekHeader, 0, wx.EXPAND)
        
        # spacer below to set the minimum size of the event area
        sizer.Add((0,35), 1, wx.EXPAND)

        self.SetSizer(sizer)
        sizer.SetSizeHints(self)
        
        # Event handlers
        self.Bind(wx.EVT_SIZE, self.OnSize)
                    
    def ResizeHeader(self):
        # column layout rules are funky:
        # - the "Week" column and the first 6 days are more or less fixed at self.dayWidth
        # - the last column (expando-button) is fixed
        # - the 7th day is flexy
        
        self.weekHeader.SetDimensions(0, self.yOffset - self.weekHeaderHeight, 
                                      self.size.width, -1)
        columnCount = self.weekHeader.GetItemCount()
        for day in range(columnCount - 2):
            self.weekHeader.SetUIExtent(day, (0, self.dayWidth))

        lastWidth = self.size.width - (self.dayWidth * (columnCount-2)) - self.scrollbarWidth
        self.weekHeader.SetUIExtent(columnCount-2, (0, lastWidth))
        self.weekHeader.SetUIExtent(columnCount-1, (0, self.scrollbarWidth))
        
    
    def OnSize(self, event):
        self._doDrawingCalculations()
        self.ResizeHeader()
        
        self.Refresh()
        event.Skip()
        
    def wxSynchronizeWidget(self):

        selectedDate = self.parent.blockItem.selectedDate
        startDate = self.parent.blockItem.rangeStart

        # Update the month button given the selected date
        lastDate = startDate + DateTime.RelativeDateTime(days=6)
        if (startDate.month == lastDate.month):
            monthText = selectedDate.Format("%B %Y")
        else:
            monthText = "%s - %s" % (startDate.Format("%B"),
                                     lastDate.Format("%B %Y"))
     
        self.monthButton.SetLabel(monthText)
        #self.monthButton.UpdateSize()

        today = DateTime.today()
        for day in range(7):
            currentDate = startDate + DateTime.RelativeDateTime(days=day)
            if currentDate == today:
                dayName = "Today"
            else:
                dayName = currentDate.Format('%a ') + str(currentDate.day)
            self.weekHeader.SetLabelText(day+1, dayName)
            
        self.Layout()
        self.Refresh()

    def toggleSize(self):
        # Toggles size between fixed and large enough to show all tasks
        if self.fixed:
            self.oldFixedSize = self.GetMinSize()
            if self.fullHeight > self.oldFixedSize.height:
                self.SetMinSize((-1, self.fullHeight + 9))
            else:
                self.SetMinSize(self.oldFixedSize)
        else:
            self.SetMinSize(self.oldFixedSize)
        self.fixed = not self.fixed

    # Drawing code

    def _doDrawingCalculations(self):
        self.size = self.GetSize()
        
        self.yOffset = self.weekHeader.GetPosition().y + self.weekHeader.GetSize().height
        self.xOffset = (self.size.width - self.scrollbarWidth) / 8
        self.dayWidth = (self.size.width - self.scrollbarWidth - self.xOffset) / self.parent.blockItem.daysPerView
        self.dayHeight = self.hourHeight * 24
        if self.parent.blockItem.dayMode:
            self.parent.columns = 1
        else:
            self.parent.columns = self.parent.blockItem.daysPerView
        self.weekHeaderHeight = self.weekHeader.GetSize().height
        

    def DrawBackground(self, dc):
        self._doDrawingCalculations()

        # Use the transparent pen for painting the background
        dc.SetPen(wx.TRANSPARENT_PEN)
        
        # Paint the entire background
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0, 0, self.size.width, self.size.height)

        dc.SetPen(self.majorLinePen)

        # Draw lines between days
        for day in range(self.parent.columns):
            dc.DrawLine(self.xOffset + (self.dayWidth * day),
                        self.yOffset,
                        self.xOffset + (self.dayWidth * day),
                        self.size.height)

        # Draw one extra line to parallel the scrollbar below
        dc.DrawLine(self.size.width - self.scrollbarWidth,
                    self.yOffset,
                    self.size.width - self.scrollbarWidth,
                    self.size.height)

    def DrawCells(self, dc):
        self._doDrawingCalculations()
        self.canvasItemList = []

        if self.parent.blockItem.dayMode:
            startDay = self.parent.blockItem.selectedDate
            width = self.size.width
        else:
            startDay = self.parent.blockItem.rangeStart
            width = self.dayWidth

        self.fullHeight = 0
        for day in range(self.parent.columns):
            currentDate = startDay + DateTime.RelativeDateTime(days=day)
            rect = wx.Rect((self.dayWidth * day) + self.xOffset, self.yOffset,
                           width, self.size.height - self.yOffset)
            self.DrawDay(dc, currentDate, rect)

        # Draw a line across the bottom of the header
        dc.SetPen(self.majorLinePen)
        dc.DrawLine(0, self.size.height - 1,
                    self.size.width, self.size.height - 1)
        dc.DrawLine(0, self.size.height - 4,
                    self.size.width, self.size.height - 4)
        dc.SetPen(self.minorLinePen)
        dc.DrawLine(0, self.size.height - 2,
                    self.size.width, self.size.height - 2)
        dc.DrawLine(0, self.size.height - 3,
                    self.size.width, self.size.height - 3)



    def DrawDay(self, dc, date, rect):
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(self.smallFont)

        x = rect.x
        y = rect.y
        w = rect.width
        h = 15

        for item in self.parent.blockItem.getDayItemsByDate(date):
            itemRect = wx.Rect(x, y, w, h)
            
            canvasItem = HeaderCanvasItem(itemRect, item)
            self.canvasItemList.append(canvasItem)
            
            # keep track of the current drag/resize box
            if self._currentDragBox and self._currentDragBox.GetItem() == item:
                self._currentDragBox = canvasItem

            if (self.parent.blockItem.selection is item):
                dc.SetBrush(self.selectionBrush)
                dc.SetPen(self.selectionPen)
                dc.DrawRectangleRect(itemRect)
                
            canvasItem.Draw(dc, self)
            
            y += h
            
        if (y > self.fullHeight):
            self.fullHeight = y
                    
    def OnCreateItem(self, unscrolledPosition):
        view = self.parent.blockItem.itsView
        newTime = self.getDateTimeFromPosition(unscrolledPosition)
        event = Calendar.CalendarEvent(view=view)
        event.InitOutgoingAttributes()
        event.ChangeStart(DateTime.DateTime(newTime.year, newTime.month,
                                            newTime.day,
                                            event.startTime.hour,
                                            event.startTime.minute))
        event.allDay = True

        self.parent.blockItem.contents.source.add(event)
        self.OnSelectItem(event)
        view.commit()
        return event

    def OnDraggingItem(self, unscrolledPosition):
        if self.parent.blockItem.dayMode:
            return
        
        newTime = self.getDateTimeFromPosition(unscrolledPosition)
        item = self._currentDragBox.GetItem()
        if (newTime.absdate != item.startTime.absdate):
            item.ChangeStart(DateTime.DateTime(newTime.year, newTime.month,
                                               newTime.day,
                                               item.startTime.hour,
                                               item.startTime.minute))
            self.Refresh()

    def OnEditItem(self, box):
        position = box.GetEditorPosition()
        size = box.GetMaxEditorSize()

        self.editor.SetItem(box.GetItem(), position, size, size.height)

    def OnDayColumnSelect(self, event):
        """
        dispatches to appropriate events in self.parent, 
        based on the column selected
        """
        
        colIndex = self.weekHeader.GetSelectedItem()
        
        # column 0, week button
        if (colIndex == 0):
            return self.parent.OnWeekSelect()
            
        # last column, the "+" expand button
        # (this may change...)
        if (colIndex == 8):
            # re-fix selection so that the expand button doesn't stay selected
            if self.parent.blockItem.dayMode:
                # ugly back-calculation of the previously selected day
                reldate = self.parent.blockItem.selectedDate - \
                          self.parent.blockItem.rangeStart
                self.weekHeader.SetSelectedItem(reldate.day+1)
            else:
                self.weekHeader.SetSelectedItem(0)
            return self.parent.OnExpand()
        
        # all other cases mean a day was selected
        # OnDaySelect takes a zero-based day, and our first day is in column 1
        return self.parent.OnDaySelect(colIndex-1)

    def getDateTimeFromPosition(self, position):
        # bound the position by the available space that the user 
        # can see/scroll to
        yPosition = max(position.y, 0)
        xPosition = max(position.x, self.xOffset)
        
        if (self.fixed):
            height = self.GetMinSize().GetWidth()
        else:
            height = self.fullHeight
            
        yPosition = min(yPosition, height)
        xPosition = min(xPosition, self.xOffset + self.dayWidth * self.parent.columns - 1)

        if self.parent.blockItem.dayMode:
            newDay = self.parent.blockItem.selectedDate
        elif self.dayWidth > 0:
            deltaDays = (xPosition - self.xOffset) / self.dayWidth
            startDay = self.parent.blockItem.rangeStart
            newDay = startDay + DateTime.RelativeDateTime(days=deltaDays)
        else:
            newDay = self.parent.blockItem.rangeStart
        return newDay

class wxWeekColumnCanvas(wxCalendarCanvas):

    def wxSynchronizeWidget(self):
        self.Refresh()

    def OnInit(self):
        super (wxWeekColumnCanvas, self).OnInit()
        
        # @@@ rationalize drawing calculations...
        self.hourHeight = 40
        
        self._scrollYRate = 10
        
        self._bgSelectionStartTime = None
        self._bgSelectionEndTime = None
        self._bgSelectionDragEnd = True
        
        self.SetVirtualSize((self.GetVirtualSize().width, self.hourHeight*24))
        self.SetScrollRate(0, self._scrollYRate)
        self.Scroll(0, (self.hourHeight*7)/self._scrollYRate)
        
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

    def ScaledScroll(self, dx, dy):
        (scrollX, scrollY) = self.CalcUnscrolledPosition(0,0)
        scrollX += dx
        scrollY += dy
        
        # rounding ensures we scroll at least one unit
        if dy < 0:
            rounding = -self._scrollYRate
        else:
            rounding = self._scrollYRate

        scaledY = (scrollY // self._scrollYRate) + rounding
        self.Scroll(scrollX, scaledY)
        
    def _doDrawingCalculations(self):
        # @@@ magic numbers
        self.size = self.GetVirtualSize()
        self.xOffset = self.size.width / 8
        if self.parent.blockItem.dayMode:
            self.parent.columns = 1
        else:
            self.parent.columns = self.parent.blockItem.daysPerView

        self.dayWidth = (self.size.width - self.xOffset) / self.parent.columns
            
        self.dayHeight = self.hourHeight * 24

    def DrawBackground(self, dc):
        self._doDrawingCalculations()

        # Use the transparent pen for painting the background
        dc.SetPen(wx.TRANSPARENT_PEN)
        
        # Paint the entire background
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0, 0, self.size.width, self.size.height + 10)

        # Set text properties for legend
        dc.SetTextForeground(self.legendColor)
        dc.SetFont(self.bigBoldFont)

        # Use topTime to draw am/pm on the topmost hour
        topCoordinate = self.CalcUnscrolledPosition((0,0))
        topTime = self.getDateTimeFromPosition(wx.Point(topCoordinate[0],
                                                        topCoordinate[1]))
        
        #bottomCoordinate = self.CalcUnscrolledPosition((
        #bottomTime = self.getDateTimeFromPosition(wx.Point(bottomCoordinate[0],
        #                                                   bottomCoordinate[1]))

        # Draw the lines separating hours
        halfHourHeight = self.hourHeight/2
        for hour in range(24):
            
            # Draw the hour legend
            if (hour > 0):
                if (hour == 1):
                    hourString = "am 1"
                elif (hour == 12): 
                    hourString = "pm 12"
                elif (hour > 12):
                    if (hour == (topTime.hour + 1)): # topmost hour
                        hourString = "pm %s" % str(hour - 12)
                    else:
                        hourString = str(hour - 12)
                else:
                    if (hour == (topTime.hour + 1)): # topmost hour
                        hourString = "am %s" % str(hour)
                    else:
                        hourString = str(hour)
                wText, hText = dc.GetTextExtent(hourString)
                dc.DrawText(hourString,
                            self.xOffset - wText - 5,
                             hour * self.hourHeight - (hText/2))
            
            # Draw the line between hours
            dc.SetPen(self.majorLinePen)
            dc.DrawLine(self.xOffset,
                         hour * self.hourHeight,
                        self.size.width,
                         hour * self.hourHeight)

            # Draw the line between half hours
            dc.SetPen(self.minorLinePen)
            dc.DrawLine(self.xOffset,
                         hour * self.hourHeight + halfHourHeight,
                        self.size.width,
                         hour * self.hourHeight + halfHourHeight)

        # Draw lines between days
        for day in range(self.parent.columns):
            if day == 0:
                dc.SetPen(self.majorLinePen)
            else:
                dc.SetPen(self.minorLinePen)
            dc.DrawLine(self.xOffset + (self.dayWidth * day), 0,
                        self.xOffset + (self.dayWidth * day), self.size.height)

        (startDay, endDay) = self.GetCurrentDateRange()
        # draw selection stuff
        if (self._bgSelectionStartTime and self._bgSelectionEndTime and
            self._bgSelectionStartTime >= startDay and
            self._bgSelectionEndTime <= endDay):
            dc.SetPen(self.majorLinePen)
            dc.SetBrush(self.selectionBrush)
            
            rects = \
                ColumnarCanvasItem.GenerateBoundsRects(self,
                                                       self._bgSelectionStartTime,
                                                       self._bgSelectionEndTime)
            for rect in rects:
                dc.DrawRectangleRect(rect)

    def sortByStartTime(self, item1, item2):
        """
        Comparison function for sorting, mostly by start time
        """
        dateResult = DateTime.cmp(item1.startTime, item2.startTime)
        
        # when two items start at the same time, we actually want to show the
        # SHORTER event last, so that painting draws it on top
        if dateResult == 0:
            dateResult = DateTime.cmp(item2.endTime, item1.endTime)
        return dateResult
        
    def sortByDepth(self, canvasItem1, canvasItem2):
        """
        Comparison by depth - sorts events by how "deep" they will appear
        on the canvas
        """
        diff = canvasItem1.GetIndentLevel() - canvasItem2.GetIndentLevel()
        if diff:
            return diff
        return self.sortByStartTime(canvasItem1.GetItem(), \
                                    canvasItem2.GetItem())
        
        
    def DrawCells(self, dc):
        self._doDrawingCalculations()
        self.canvasItemList = []

        (startDay, endDay) = self.GetCurrentDateRange()
        
        # Set up fonts and brushes for drawing the events
        dc.SetTextForeground(wx.BLACK)
        dc.SetBrush(wx.WHITE_BRUSH)

        # we sort the items so that when drawn, the later events are drawn last
        # so that we get proper stacking
        visibleItems = list(self.parent.blockItem.getItemsInRange(startDay, endDay))
        visibleItems.sort(self.sortByStartTime)
                
        boundingRect = wx.Rect(self.xOffset, 0, self.size.width, self.size.height)
        
        # First generate a sorted list of ColumnarCanvasItems
        for item in visibleItems:
                                               
            canvasItem = ColumnarCanvasItem(item, self)
            self.canvasItemList.append(canvasItem)

            if self._currentDragBox and self._currentDragBox.GetItem() == item:
                self._currentDragBox = canvasItem                

        # now generate conflict info
        self.CheckConflicts()
        
        # canvasItemList has to be sorted by depth
        # should be relatively quick because the canvasItemList is already
        # sorted by startTime. If no conflicts, this is an O(n) operation
        self.canvasItemList.sort(self.sortByDepth)
        
        selectedBox = None        
        # finally, draw the items
        for canvasItem in self.canvasItemList:

            # drawing rects should be updated to reflect conflicts
            canvasItem.UpdateDrawingRects()
            
            # save the selected box to be drawn last
            if self.parent.blockItem.selection is canvasItem.GetItem():
                selectedBox = canvasItem
            else:
                canvasItem.Draw(dc, boundingRect, self)
            
        # now draw the current item on top of everything else
        if selectedBox:
            dc.SetBrush(self.selectionBrush)
            selectedBox.Draw(dc, boundingRect, self)
            

    def CheckConflicts(self):
        for itemIndex, canvasItem in enumerate(self.canvasItemList):
            # since these are sorted, we only have to check the items 
            # that come after the current one
            for innerItem in self.canvasItemList[itemIndex+1:]:
                # we know we're done when we stop hitting conflicts
                # 
                # have a guarantee that innerItem.startTime >= item.endTime
                # Since item.endTime < item.startTime, we know we're
                # done
                if innerItem.GetItem().startTime >= canvasItem.GetItem().endTime: break
                
                # item and innerItem MUST conflict now
                canvasItem.AddConflict(innerItem)
            
            # we've now found all conflicts for item, do we need to calculate
            # depth or anything?
            # first theory: leaf children have a maximum conflict depth?
            canvasItem.CalculateConflictDepth()


    def OnKeyPressed(self, event):
        # create an event here - unfortunately the panel can't get focus, so it
        # can't recieve keystrokes yet...
        pass
            
    # handle mouse related actions: move, resize, create, select
    
    def OnSelectItem(self, item):
        if item:
            # clear background selection
            self._bgSelectionStartTime = self._bgSelectionEndTime = None
        
        super(wxWeekColumnCanvas, self).OnSelectItem(item)
        
    def OnSelectNone(self, unscrolledPosition):
        self._bgSelectionStartTime = self.getDateTimeFromPosition(unscrolledPosition)
        self._bgSelectionDragEnd = True
        self._bgSelectionEndTime = self._bgSelectionStartTime + \
            DateTime.RelativeDateTime(minutes=30)
            
        # set focus on the calendar so that we can receive key events
        # (as of this writing, wxPanel can't recieve focus, so this is a no-op)
        self.SetFocus()
        super(wxWeekColumnCanvas, self).OnSelectNone(unscrolledPosition)
        
    def OnEditItem(self, box):
        position = self.CalcScrolledPosition(box.GetEditorPosition())
        size = box.GetMaxEditorSize()

        textPos = wx.Point(position.x + 8, position.y + 15)
        textSize = wx.Size(size.width - 13, size.height - 20)

        self.editor.SetItem(box.GetItem(), textPos, textSize, self.smallFont.GetPointSize()) 

    def OnCreateItem(self, unscrolledPosition):
        # @@@ this code might want to live somewhere else, refactored
        view = self.parent.blockItem.itsView
        event = Calendar.CalendarEvent(view=view)
        newTime = self.getDateTimeFromPosition(unscrolledPosition)
        event.InitOutgoingAttributes()
        event.ChangeStart(newTime)

        # ugh, this is a hack to work around the whole ItemCollection stuff
        # see bug 2749 for some background
        self.parent.blockItem.contents.source.add(event)
        
        self.OnSelectItem(event)

        # @@@ Bug#1854 currently this is too slow,
        # and the event causes flicker
        #view.commit()
        canvasItem = ColumnarCanvasItem(event, self)
        
        # only problem here is that we haven't checked for conflicts
        canvasItem.UpdateDrawingRects()
        canvasItem.SetResizeMode(canvasItem.RESIZE_MODE_END)
        return canvasItem
        
    
    def OnBeginResizeItem(self):
        self._lastUnscrolledPosition = self._dragStartUnscrolled
        self.StartDragTimer()
        pass
        
    def OnEndResizeItem(self):
        self.StopDragTimer()
        self._originalDragBox.ResetResizeMode()
        pass
        
    def OnResizingItem(self, unscrolledPosition):
        newTime = self.getDateTimeFromPosition(unscrolledPosition)
        item = self._currentDragBox.GetItem()
        resizeMode = self.GetResizeMode()
        delta = DateTime.DateTimeDelta(0, 0, 15)
        
        # make sure we're changing by at least delta 
        if (resizeMode == ColumnarCanvasItem.RESIZE_MODE_END and 
            newTime > (item.startTime + delta)):
            item.endTime = newTime
        elif (resizeMode == ColumnarCanvasItem.RESIZE_MODE_START and 
              newTime < (item.endTime - delta)):
            item.startTime = newTime
        self.Refresh()
    
    def OnDragTimer(self):
        """
        This timer goes off while we're dragging/resizing
        """
        scrolledPosition = self.CalcScrolledPosition(self._dragCurrentUnscrolled)
        self.ScrollIntoView(scrolledPosition)
    
    def StartDragTimer(self):
        self.scrollTimer = ClosureTimer(self.OnDragTimer)
        self.scrollTimer.Start(100, wx.TIMER_CONTINUOUS)
    
    def StopDragTimer(self):
        self.scrollTimer.Stop()
        self.scrollTimer = None
        
    def OnBeginDragItem(self):
        self.StartDragTimer()
        pass
        
    def OnEndDragItem(self):
        self.StopDragTimer()
        pass
        
    def OnDraggingNone(self, unscrolledPosition):
        dragDateTime = self.getDateTimeFromPosition(unscrolledPosition)
        if self._bgSelectionDragEnd:
            self._bgSelectionEndTime = dragDateTime
        else:
            self._bgSelectionStartTime = dragDateTime
            
        if (self._bgSelectionEndTime < self._bgSelectionStartTime):
            # swap values, drag the other end
            self._bgSelectionDragEnd = not self._bgSelectionDragEnd
            (self._bgSelectionStartTime, self._bgSelectionEndTime) = \
                (self._bgSelectionEndTime, self._bgSelectionStartTime)
        self.Refresh()
            
        
    def OnDraggingItem(self, unscrolledPosition):
        # at the start of the drag, the mouse was somewhere inside the
        # dragbox, but not necessarily exactly at x,y
        #
        # so account for the original offset within the ORIGINAL dragbox so the 
        # mouse cursor stays in the same place relative to the original box
        
        # We need to figure out where the original drag started,
        # so the mouse stays in the same position relative to
        # the origin of the item
        (boxX,boxY) = self._originalDragBox.GetDragOrigin()
        dy = self._dragStartUnscrolled.y - boxY
        
        # dx is tricky: we want the user to be able to drag left/right within
        # the confines of the current day, but if they cross a day threshold,
        # then we want to shift the whole event over one day
        # to do this, we need to round dx to the nearest dayWidth
        dx = self._dragStartUnscrolled.x - boxX
        dx = int(dx/self.dayWidth) * self.dayWidth
        position = wx.Point(unscrolledPosition.x - dx, unscrolledPosition.y - dy)
        
        newTime = self.getDateTimeFromPosition(position)
        item = self._currentDragBox.GetItem()
        if ((newTime.absdate != item.startTime.absdate) or
            (newTime.hour != item.startTime.hour) or
            (newTime.minute != item.startTime.minute)):
            item.ChangeStart(newTime)
            self.Refresh()

    def GetResizeMode(self):
        """
        Helper method for drags
        """
        return self._originalDragBox.getResizeMode(self._dragStartUnscrolled)
        
    def getDateTimeFromPosition(self, position):
        # bound the position by the available space that the user 
        # can see/scroll to
        yPosition = max(position.y, 0)
        xPosition = max(position.x, self.xOffset)
        
        yPosition = min(yPosition, self.hourHeight * 24 - 1)
        xPosition = min(xPosition, self.xOffset + self.dayWidth * self.parent.columns - 1)
        
        (startDay, endDay) = self.GetCurrentDateRange()

        # @@@ fixes Bug#1831, but doesn't really address the root cause
        # (the window is drawn with (0,0) virtual size on mac)
        if self.dayWidth > 0:
            deltaDays = (xPosition - self.xOffset) / self.dayWidth
        else:
            deltaDays = 0
        
        deltaHours = yPosition / self.hourHeight
        deltaMinutes = ((yPosition % self.hourHeight) * 60) / self.hourHeight
        deltaMinutes = int(deltaMinutes/15) * 15
        newTime = startDay + DateTime.RelativeDateTime(days=deltaDays,
                                                       hours=deltaHours,
                                                       minutes=deltaMinutes)
        return newTime

    def getPositionFromDateTime(self, datetime):
        (startDay, endDay) = self.GetCurrentDateRange()
        
        if datetime < startDay or \
           datetime > endDay:
            raise ValueError, "Must be visible on the calendar"
            
        delta = datetime - startDay
        x = (self.dayWidth * delta.day) + self.xOffset
        y = int(self.hourHeight * (datetime.hour + datetime.minute/float(60)))
        return wx.Point(x, y)
        
class WeekBlock(CalendarBlock):
    def __init__(self, *arguments, **keywords):
        super(WeekBlock, self).__init__ (*arguments, **keywords)

    def initAttributes(self):
        if not self.hasLocalAttributeValue('rangeStart'):
            self.dayMode = False
            self.setRange(DateTime.today())
        if not self.hasLocalAttributeValue('rangeIncrement'):
            self.rangeIncrement = DateTime.RelativeDateTime(days=self.daysPerView)
            
    def instantiateWidget(self):
        # @@@ KCP move to a callback that gets called from parcel loader
        # after item has all of its attributes assigned from parcel xml
        self.initAttributes()
        
        return wxWeekPanel(self.parentBlock.widget,
                           Block.Block.getWidgetID(self))

    def setRange(self, date):
        if self.daysPerView == 7:
            # if in week mode, start at the beginning of the week
            delta = DateTime.RelativeDateTime(days=-6,
                                              weekday=(DateTime.Sunday, 0))
            self.rangeStart = date + delta
        else:
            # otherwise, stick with the given date
            self.rangeStart = date
            
        if self.dayMode:
            self.selectedDate = date
        else:
            self.selectedDate = self.rangeStart

class wxInPlaceEditor(wx.TextCtrl):
    def __init__(self, *arguments, **keywords):
        super(wxInPlaceEditor, self).__init__(style=wx.TE_PROCESS_ENTER | wx.NO_BORDER,
                                              *arguments, **keywords)
        
        self.item = None
        self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnTextEnter)
        self.Hide()

        #self.editor.Bind(wx.EVT_CHAR, self.OnChar)
        parent = self.GetParent()
        parent.Bind(wx.EVT_SIZE, self.OnSize)

    def SaveItem(self):
        if ((self.item != None) and (not self.IsBeingDeleted())):
            self.item.displayName = self.GetValue()
        
    def OnTextEnter(self, event):
        self.SaveItem()
        self.Hide()
        event.Skip()

    def OnChar(self, event):
        if (event.KeyCode() == wx.WXK_RETURN):
            if self.item != None:
                self.item.displayName = self.GetValue()
            self.Hide()
        event.Skip()

    def SetItem(self, item, position, size, pointSize):
        self.item = item
        self.SetValue(item.displayName)

        newSize = wx.Size(size.width, size.height)

        # GTK doesn't like making the editor taller than
        # the font, plus it doesn't honor the NOBORDER style
        # so we have to include 4 pixels for each border
        if '__WXGTK__' in wx.PlatformInfo:
            newSize.height = pointSize + 8

        self.SetSize(newSize)
        self.Move(position)

        self.SetInsertionPointEnd()
        self.SetSelection(-1, -1)
        self.Show()
        self.SetFocus()

    def OnSize(self, event):
        self.Hide()
        event.Skip()

class wxMonthCanvas(wxCalendarCanvas, CalendarEventHandler):
    def __init__(self, *arguments, **keywords):
        super(wxMonthCanvas, self).__init__(*arguments, **keywords)

    def OnInit(self):
        super(wxMonthCanvas, self).OnInit()

        # Setup the navigation buttons
        today = DateTime.today()
        
        self.prevButton = CollectionCanvas.CanvasBitmapButton(self, "application/images/backarrow.png")
        self.nextButton = CollectionCanvas.CanvasBitmapButton(self, "application/images/forwardarrow.png")
        self.monthButton = CollectionCanvas.CanvasTextButton(self, today.Format("%B %Y"),
                                                             self.bigFont, self.bigFontColor,
                                                             self.bgColor)

        self.monthButton.UpdateSize()

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add((0,0), 1, wx.EXPAND, 5)
        box.Add((0,0), 1, wx.EXPAND, 5)
        box.Add(self.monthButton, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        box.Add((0,0), 1, wx.EXPAND, 5)
        box.Add(self.prevButton, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        box.Add(self.nextButton, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        self.SetSizer(box)
                                            
        self.Bind(wx.EVT_BUTTON, self.OnPrev, self.prevButton)
        self.Bind(wx.EVT_BUTTON, self.OnNext, self.nextButton)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnSize(self, event):
        self.Refresh()
        event.Skip()

    def wxSynchronizeWidget(self):
        self.monthButton.SetLabel(self.blockItem.rangeStart.Format("%B %Y"))
        self.Layout()
        self.Refresh()

    # Drawing logic

    def _doDrawingCalculations(self):
        self.size = self.GetVirtualSize()
        self.yOffset = 50
        self.dayWidth = self.size.width / 7
        self.dayHeight = (self.size.height - self.yOffset) / 6
    
    def DrawBackground(self, dc):
        self._doDrawingCalculations()

        # Use the transparent pen for drawing the background rectangles
        dc.SetPen(wx.TRANSPARENT_PEN)

        # Draw the background
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0, 0, self.size.width, self.size.height + 10)
        
        # Set up pen for drawing the grid
        dc.SetPen(self.majorLinePen)

        # Draw the lines between the days
        for i in range(1, 7):
            dc.DrawLine(self.dayWidth * i, self.yOffset,
                        self.dayWidth * i, self.size.height)

        # Draw the lines between the weeks
        for i in range(6):
            dc.DrawLine(0, (i * self.dayHeight) + self.yOffset,
                        self.size.width,
                         (i * self.dayHeight) + self.yOffset)


    def DrawCells(self, dc):
        self._doDrawingCalculations()
        self.canvasItemList = []
        
        # Delegate the drawing of each day
        startDay = self.blockItem.rangeStart + \
                   DateTime.RelativeDateTime(days=-6, weekday=(DateTime.Sunday, 0))

        # Draw each day in the month
        for week in range(6):
            for day in range(7):
                currentDate = startDay + DateTime.RelativeDateTime(days=(week*7 + day))
                rect = wx.Rect(self.dayWidth * day,
                               self.dayHeight * week + self.yOffset,
                               self.dayWidth,
                               self.dayHeight)
                self.DrawDay(dc, currentDate, rect)

        # Draw the weekdays
        for i in range(7):
            weekday = startDay + DateTime.RelativeDateTime(days=i)
            rect = wx.Rect(self.dayWidth * i,
                           self.yOffset,
                           self.dayWidth, 20) # Related to font height?
            self.DrawWeekday(dc, weekday, rect)


    def DrawDay(self, dc, date, rect):
        # Scaffolding, we'll get more sophisticated here

        dc.SetTextForeground(self.bigFontColor)
        dc.SetFont(self.bigFont)

        # Draw the day header
        # Add logic to treat "today" or "not in current month" specially
        dc.DrawText(date.Format("%d"), rect.x, rect.y)
        
        x = rect.x
        y = rect.y + 10
        w = rect.width
        h = 15

        dc.SetTextForeground(self.smallFontColor)
        dc.SetFont(self.smallFont)

        for item in self.blockItem.getItemsInRange(date, date + DateTime.RelativeDateTime(days=1)):
            itemRect = wx.Rect(x, y, w, h)
            canvasItem = CollectionCanvas.CanvasItem(itemRect, item)
            self.canvasItemList.append(canvasItem)

            # keep track of the current drag/resize box
            if self._currentDragBox and self._currentDragBox.GetItem() == item:
                self._currentDragBox = canvasItem
                
            canvasItem.Draw(dc, itemRect, self.blockItem.selection is item)
            y += h

    def DrawWeekday(self, dc, weekday, rect):
        dc.SetTextForeground(self.bigFontColor)
        dc.SetFont(self.bigFont)

        dayName = weekday.Format('%a')
        self.DrawCenteredText(dc, dayName, rect)

    # handle mouse related actions: move, create

    def OnCreateItem(self, unscrolledPosition):
        # @@@ this code might want to live somewhere else, refactored
        view = self.blockItem.itsView
        newTime = self.getDateTimeFromPosition(unscrolledPosition)
        event = Calendar.CalendarEvent(view=view)
        event.InitOutgoingAttributes()
        event.ChangeStart(DateTime.DateTime(newTime.year, newTime.month,
                                            newTime.day,
                                            event.startTime.hour,
                                            event.startTime.minute))

        self.blockItem.contents.source.add(event)
        self.OnSelectItem(event)
        
        # @@@ Bug#1854 currently this is too slow,
        # and the event causes flicker
        view.commit()
        return event

    def OnDraggingItem(self, unscrolledPosition):
        newTime = self.getDateTimeFromPosition(unscrolledPosition)
        item = self._currentDragBox.GetItem()
        if (newTime.absdate != item.startTime.absdate):
            item.ChangeStart(DateTime.DateTime(newTime.year, newTime.month,
                                               newTime.day,
                                               item.startTime.hour,
                                               item.startTime.minute))
            self.Refresh()

    def getDateTimeFromPosition(self, position):
        # x and y in whole canvas coordinates
        
        # the first day displayed in the month view
        startDay = self.blockItem.getStartDay()

        # the number of days over
        deltaDays = position.x / self.dayWidth

        # the number of weeks over
        deltaWeeks = (position.y - self.yOffset) / self.dayHeight

        newDay = startDay + DateTime.RelativeDateTime(days=deltaDays,
                                                      weeks=deltaWeeks)
        return newDay
    

class MonthBlock(CalendarBlock):
    def __init__(self, *arguments, **keywords):
        super(MonthBlock, self).__init__(*arguments, **keywords)

        self.rangeIncrement = DateTime.RelativeDateTime(months=1)
        self.setRange(DateTime.today())

    def instantiateWidget(self):
        return wxMonthCanvas(self.parentBlock.widget,
                             Block.Block.getWidgetID(self))

    def setRange(self, date):
        # override set range to pick the first day of the month
        self.rangeStart = DateTime.DateTime(date.year, date.month)
        self.selectedDate = self.rangeStart

    def getStartDay(self):
        """ Returns the starting day of the month displayed.
        """
        startDay = self.rangeStart + \
                   DateTime.RelativeDateTime(days=-6,
                                             weekday=(DateTime.Sunday, 0))
        return startDay



    







