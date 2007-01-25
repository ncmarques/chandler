#   Copyright (c) 2003-2006 Open Source Applications Foundation
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


from osaf.framework.blocks import *
from osaf.framework.blocks.calendar import *
from osaf.views.main.Main import *
from osaf.views.main.SideBar import *
from osaf.pim.structs import SizeType, RectType
from osaf import pim
from osaf import messages
from i18n import ChandlerMessageFactory as _
import osaf.pim.calendar
from application import schema
from repository.item.Item import MissingClass
import wx.grid

def makeMainView(parcel):
    repositoryView = parcel.itsView

    globalBlocks = schema.ns("osaf.framework.blocks", repositoryView)
    main = schema.ns("osaf.views.main", repositoryView)
    app_ns = schema.ns("osaf.app", repositoryView)
    pim_ns = schema.ns("osaf.pim", repositoryView)

    # these reference each other... ugh!
    RTimer = ReminderTimer.template('ReminderTimer').install(parcel)
    main.ReminderTime.destinationBlockReference = RTimer

    ReminderTimer.update(
        parcel, 'ReminderTimer',
        event = main.ReminderTime,
        contents = pim_ns.itemsWithReminders)

    SidebarBranchPointDelegateInstance = SidebarBranchPointDelegate.update(
        parcel, 'SidebarBranchPointDelegateInstance',
        calendarTemplatePath = '//parcels/osaf/views/main/CalendarSummaryViewTemplate',
        dashboardTemplatePath = '//parcels/osaf/views/main/DashboardSummaryViewTemplate',
        searchResultsTemplatePath = '//parcels/osaf/views/main/SearchResultsViewTemplate')
    
    IconButton = SSSidebarIconButton.update(
        parcel, 'IconButton',
        buttonName = 'Icon',
        buttonOffsets = [0,21,19])
    
    SharingButton = SSSidebarSharingButton.update(
        parcel, 'SharingIcon',
        buttonName = 'SharingIcon',
        buttonOffsets = [-17,-1,16])

    sidebarSelectionCollection = pim.IndexedSelectionCollection.update(
        parcel, 'sidebarSelectionCollection',
        source = app_ns.sidebarCollection)

    Sidebar = SidebarBlock.template(
        'Sidebar',
        characterStyle = globalBlocks.SidebarRowStyle,
        columns = [Column.update(parcel, 'SidebarColName',
                                 heading = u'',
                                 scaleColumn = wx.grid.Grid.GRID_COLUMN_SCALABLE,
                                 attributeName = u'displayName')],

        scaleWidthsToFit = True,
        rowHeight = 19,
        border = RectType(0, 0, 4, 0),
        editRectOffsets = [22, -17, 0],
        buttons = [IconButton, SharingButton],
        contents = sidebarSelectionCollection,
        elementDelegate = 'osaf.views.main.SideBar.SidebarElementDelegate',
        hideColumnHeadings = True,
        defaultEditableAttribute = u'displayName',
        filterClass = osaf.pim.calendar.Calendar.EventStamp,
        disallowOverlaysForFilterClasses = [MissingClass,
                                          osaf.pim.mail.MailStamp,
                                          osaf.pim.tasks.TaskStamp]
        ).install(parcel)
    Sidebar.contents.selectItem (pim_ns.allCollection)

    miniCal = MiniCalendar.template(
        'MiniCalendar',
        contents = pim_ns.allCollection,
        calendarContainer = None,
        stretchFactor = 0.0).install(parcel)

    toolbarIconSize = SizeType(32, 32)    

    ApplicationBar = Toolbar.template(
        'ApplicationBar',
        stretchFactor = 0.0,
        toolSize = toolbarIconSize,
        buttonsLabeled = True,
        separatorWidth = 20,
        mainFrameToolbar = True,
        childrenBlocks = [
            ToolbarItem.template('ApplicationBarAllButton',
                event = main.ApplicationBarAll,
                bitmap = 'ApplicationBarAll.png',
                title = _(u"All"),
                toolbarItemKind = 'Radio',
                helpString = _(u'View all items')),
            ToolbarItem.template('ApplicationBarMailButton',
                event = main.ApplicationBarMail,
                bitmap = 'ApplicationBarMail.png',
                title = _(u'Mail'),
                toolbarItemKind = 'Radio',
                helpString = _(u'View messages')),
            ToolbarItem.template('ApplicationBarTaskButton',
                event = main.ApplicationBarTask,
                bitmap = 'ApplicationBarTask.png',
                title = _(u'Tasks'),
                toolbarItemKind = 'Radio',
                helpString = _(u'View tasks')),
            ToolbarItem.template('ApplicationBarEventButton',
                event = main.ApplicationBarEvent,
                bitmap = 'ApplicationBarEvent.png',
                title = _(u'Calendar'),
                selected = True,
                toolbarItemKind = 'Radio',
                helpString = _(u'View events')),
            ToolbarItem.template('ApplicationSeparator1',
                toolbarItemKind = 'Separator'),
            ToolbarItem.template('ApplicationBarSyncButton',
                event = main.SyncAll,
                bitmap = 'ApplicationBarSync.png',
                title = _(u'Sync All'),
                toolbarItemKind = 'Button',
                helpString = _(u'Sync all shared collections and download new messages')),
            ToolbarItem.template('ApplicationBarNewButton',
                event = main.NewItem,
                bitmap = 'ApplicationBarNew.png',
                title = _(u'New'),
                toolbarItemKind = 'Button',
                helpString = _(u'Create a new item')),
            ToolbarItem.template('ApplicationBarReplyButton',
                event = main.ReplyMessage,
                bitmap = 'ApplicationBarReply.png',
                title = messages.REPLY,
                toolbarItemKind = 'Button',
                helpString = _(u'Reply to sender of selected message')),
            ToolbarItem.template('ApplicationBarReplyAllButton',
                event = main.ReplyAllMessage,
                bitmap = 'ApplicationBarReplyAll.png',
                title = messages.REPLY_ALL,
                toolbarItemKind = 'Button',
                helpString = _(u'Reply to all recipients of selected message')),
            ToolbarItem.template('ApplicationBarForwardButton',
                event = main.ForwardMessage,
                bitmap = 'ApplicationBarForward.png',
                title = messages.FORWARD,
                toolbarItemKind = 'Button',
                helpString = _(u'Forward selected message')),
            ToolbarItem.template('ApplicationSeparator2',
                toolbarItemKind = 'Separator'),
            ToolbarItem.template('TriageButton',
                event = main.Triage,
                title = _(u"Triage"),
                bitmap = 'ApplicationBarTriage.png',
                toolbarItemKind = 'Button',
                helpString = _(u'Sort items by triage status')),
            ToolbarItem.template('ApplicationSeparator3',
                toolbarItemKind = 'Separator'),
            ToolbarItem.template('ApplicationBarSendButton',
                event = main.SendShareItem,
                bitmap = 'ApplicationBarSend.png',
                title = messages.SEND,
                toolbarItemKind = 'Button',
                helpString = _(u'Send selected message')),
            ToolbarItem.template('ApplicationSeparator4',
                toolbarItemKind = 'Separator'),
            ToolbarItem.template('ApplicationBarQuickEntry',
                event = main.QuickEntry,
                text = u"", # text value displayed in the control
                toolbarItemKind = 'QuickEntry',
                size = SizeType (200,-1),
                helpString = _(u'Quick entry field: enter search string, or command beginning with "/"')),
        ]
    ) # Toolbar ApplicationBar

    MainViewInstance = MainView.template(
        'MainView',
        size = SizeType (1024, 720),
        orientationEnum='Vertical',
        eventBoundary = True,
        displayName = _(u'Chandler\'s MainView'),
        eventsForNamedLookup=[
            main.RequestSelectSidebarItem,
            main.SendMail,
            main.SelectedDateChanged,
            main.ShareItem,
            main.DayMode,
            main.ApplicationBarEvent,
            main.ApplicationBarTask,
            main.ApplicationBarMail,
            main.ApplicationBarAll,
            ],
        childrenBlocks = [
            main.MenuBar,
            StatusBar.template('StatusBar'),
            ReminderTimer.template('ReminderTimer',
                                   event = main.ReminderTime,
                                   contents=pim_ns.itemsWithReminders),
            BoxContainer.template('ToolbarContainer',
                orientationEnum = 'Vertical',
                bufferedDraw = True,
                childrenBlocks = [
                    ApplicationBar,
                    BoxContainer.template('SidebarContainerContainer',
                        border = RectType(4, 0, 0, 0),
                        childrenBlocks = [
                            SplitterWindow.template('SidebarContainer',
                                stretchFactor = 0.0,
                                border = RectType(0, 0, 0, 4.0),
                                splitPercentage = 0.42,
                                splitController = miniCal,
                                childrenBlocks = [
                                    Sidebar,
                                    BoxContainer.template('PreviewAndMiniCalendar',
                                        orientationEnum = 'Vertical',
                                        childrenBlocks = [
                                            PreviewArea.template('PreviewArea',
                                                contents = pim_ns.allCollection,
                                                calendarContainer = None,
                                                timeCharacterStyle = \
                                                    CharacterStyle.update(parcel, 
                                                                          'PreviewTimeStyle', 
                                                                          fontSize = 10,
                                                                          fontStyle = 'bold'),
                                                eventCharacterStyle = \
                                                    CharacterStyle.update(parcel, 
                                                                          'PreviewEventStyle', 
                                                                          fontSize = 11),
                                                linkCharacterStyle = \
                                                    CharacterStyle.update(parcel, 
                                                                          'PreviewLinkStyle', 
                                                                          fontSize = 11,
                                                                          fontStyle = 'underline'),
                                                stretchFactor = 0.0,
                                                miniCalendar = miniCal),
                                            miniCal
                                            ]) # BoxContainer PreviewAndMiniCalendar
                                    ]), # SplitterWindow SidebarContainer
                            BranchPointBlock.template('SidebarBranchPointBlock',
                                delegate = SidebarBranchPointDelegateInstance,
                                detailItem = pim_ns.allCollection,
                                selectedItem = pim_ns.allCollection,
                                detailItemCollection = pim_ns.allCollection,
                                setFocus = True),
                            ]) # BoxContainer SidebarContainerContainer
                    ]) # BoxContainer ToolbarContainer
            ]).install(parcel) # MainViewInstance MainView

    MainBranchPointDelegate = BranchPointDelegate.update(parcel, 
        'MainBranchPointDelegate')

    MainBranchPointBlock = BranchPointBlock.template(
        'MainBranchPointBlock',
        detailItem = MainViewInstance,
        selectedItem = MainViewInstance,
        childrenBlocks = [MainViewInstance],
        delegate = MainBranchPointDelegate).install(parcel)

    CPIATestMainView = schema.ns("osaf.views.cpiatest", repositoryView).MainView
    CPIATest2MainView = schema.ns("osaf.views.cpiatest2", repositoryView).MainView
    FrameWindow.update(
        parcel, 'MainViewRoot',
        blockName = 'MainViewRoot',
        windowTitle = _(u"Chandler"),
        size = SizeType(1024,720),
        eventBoundary=True,
        views = {'MainView' : MainViewInstance,
                 'CPIATestMainView' : CPIATestMainView,
                 'CPIATest2MainView' : CPIATest2MainView},
        activeView = MainViewInstance,
        childrenBlocks = [MainBranchPointBlock])

    # Add certstore UI
    schema.synchronize(repositoryView, "osaf.framework.certstore.blocks")

    return MainViewInstance

