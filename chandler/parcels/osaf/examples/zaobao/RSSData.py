__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import application.Globals as Globals
from repository.item.Item import Item
from repository.util.Path import Path
from repository.parcel.Parcel import Parcel
from OSAF.contentmodel.ContentModel import ContentItem
import mx.DateTime
import types
import feedparser


##
# ZaoBaoParcel
##
class ZaoBaoParcel(Parcel):
    def __init__(self, name, parent, kind):
        Parcel.__init__(self, name, parent, kind)

    def _setUUIDs(self, parent):

        # hackery to avoid threading conflicts
        ZaoBaoParcel.RSSItemParentID = parent.itsUUID
        
        ZaoBaoParcel.RSSChannelKindID = self.find('RSSChannel').itsUUID
        ZaoBaoParcel.RSSItemKindID = self.find('RSSItem').itsUUID

    def onItemLoad(self):
        super(ZaoBaoParcel, self).onItemLoad()

        # @@@ hackery to avoid threading conflicts
        repository = self.getRepository()
        parent = repository.find('//userdata/zaobaoitems')
        
        self._setUUIDs(parent)

    def startupParcel(self):
        super(ZaoBaoParcel, self).startupParcel()

        # @@@ hackery to avoid threading conflicts
        # Create a separate parent for RSSItems
        repository = self.getRepository()
        parent = repository.find('//userdata/zaobaoitems')
        if not parent:
            itemKind = repository.find('//Schema/Core/Item')
            userdata = repository.find('//userdata')
            if not userdata:
                userdata = itemKind.newItem('userdata', repository)
            parent = itemKind.newItem('zaobaoitems', userdata)
        
        self._setUUIDs(parent)

    # @@@ hackery to avoid threading conflicts
    # Keep track of a separate parent for RSSItems

    def getRSSItemParent(cls):
        assert cls.RSSItemParentID, "ZaoBaoParcel not yet loaded"
        return Globals.repository[cls.RSSItemParentID]

    getRSSItemParent = classmethod(getRSSItemParent)

    def getRSSChannelKind(cls):
        assert cls.RSSChannelKindID, "ZaoBaoParcel not yet loaded"
        return Globals.repository[cls.RSSChannelKindID]

    getRSSChannelKind = classmethod(getRSSChannelKind)

    def getRSSItemKind(cls):
        assert cls.RSSItemKindID, "ZaoBaoParcel not yet loaded"
        return Globals.repository[cls.RSSItemKindID]

    getRSSItemKind = classmethod(getRSSItemKind)
    
    # The parcel knows the UUIDs for the Kinds, once the parcel is loaded
    RSSChannelKindID = None
    RSSItemKindID = None


def SetAttribute(self, data, attr, nattr=None, encoding=None):
    if not nattr:
        nattr = attr
    value = data.get(attr)
    if value:
        if encoding:
            value = unicode(value, encoding)
        self.setAttributeValue(nattr, value)

def SetAttributes(self, data, attributes, encoding=None):
    if type(attributes) == types.DictType:
        for attr, nattr in attributes.items():
            SetAttribute(self, data, attr, nattr=nattr, encoding=encoding)
    elif type(attributes) == types.ListType:
        for attr in attributes:
            SetAttribute(self, data, attr, encoding=encoding)


##
# RSSChannel
##
def NewChannelFromURL(url, update = True):
    data = feedparser.parse(url)

    if data['channel'] == {} or data['status'] == 404:
        return None

    channel = RSSChannel()
    channel.url = url

    if update:
        try:
            channel.Update(data)
        except:
            channel.delete()
            channel = None

    return channel

class RSSChannel(ContentItem):
    def __init__(self, name=None, parent=None, kind=None):
        # @@@ parent is hackery to avoid threading conflicts
        if not parent:
            parent = ZaoBaoParcel.getRSSItemParent()
        if not kind:
            kind = ZaoBaoParcel.getRSSChannelKind()
        super(RSSChannel, self).__init__(name, parent, kind)
        self.items = []

    def Update(self):
        etag = self.getAttributeValue('etag', default=None)
        lastModified = self.getAttributeValue('lastModified', default=None)
        if lastModified:
            lastModified = lastModified.tuple()

        # fetch the data
        data = feedparser.parse(self.url, etag, lastModified)

        # get the encoding
        encoding = data.get('encoding', 'latin_1')

        # set etag
        SetAttribute(self, data, 'etag')

        # set lastModified
        modified = data.get('modified')
        if modified:
            self.lastModified = mx.DateTime.mktime(modified)

        self._DoChannel(data['channel'], encoding)
        self._DoItems(data['items'], encoding)

    def _DoChannel(self, data, encoding):
        # fill in the item
        attrs = {'title':'displayName'}
        SetAttributes(self, data, attrs, encoding)

        attrs = ['link', 'description', 'copyright', 'creator', 'category', 'language']
        SetAttributes(self, data, attrs, encoding)

        date = data.get('date')
        if date:
            self.date = mx.DateTime.DateTimeFrom(date)

    def _DoItems(self, items, encoding):
        # make children
        for itemData in items:
            #print 'new item'
            item = RSSItem()
            item.Update(itemData, encoding)
            self.addValue('items', item)


##
# RSSItem
##
class RSSItem(ContentItem):
    def __init__(self, name=None, parent=None, kind=None):
        # @@@ parent is hackery to avoid threading conflicts
        if not parent:
            parent = ZaoBaoParcel.getRSSItemParent()
        if not kind:
            kind = ZaoBaoParcel.getRSSItemKind()
        super(RSSItem, self).__init__(name, parent, kind)

    def Update(self, data, encoding):
        # fill in the item
        attrs = {'title':'displayName'}
        SetAttributes(self, data, attrs, encoding)

        attrs = ['description', 'creator', 'link', 'category']
        SetAttributes(self, data, attrs, encoding)

        date = data.get('date')
        if date:
            self.date = mx.DateTime.DateTimeFrom(date)
