#   Copyright (c) 2004-2007 Open Source Applications Foundation
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


from itertools import izip

from chandlerdb.util.c import isuuid, Nil, Default
from chandlerdb.item.c import isitem, isitemref
from chandlerdb.item.ItemError import RecursiveDeleteError
from chandlerdb.item.Item import Item
from chandlerdb.item.Sets import AbstractSet
from chandlerdb.item.RefCollections import RefList
from chandlerdb.item.PersistentCollections import PersistentCollection


class Cloud(Item):

    def getItems(self, item, cloudAlias, items=None, references=None,
                 trace=None):
        """
        Gather all items in the cloud from a given item entrypoint.

        Items are found at each endpoint of this cloud and are included into
        the returned result set and the optional C{items} and C{references}
        dictionaries according to the following endpoint policies:

            - C{byValue}: the item is added to the result set and is added
              to the C{items} dictionary.

            - C{byRef}: the item is not added to the result set but is added
              to the C{references} dictionary.

            - C{byCloud}: the item is added to the result set and is used
              as an entrypoint for a cloud gathering operation. The cloud
              used is determined in this order:

                  - the cloud specified on the endpoint

                  - the cloud obtained by the optional C{cloudAlias}

                  - the first cloud specified for the item's kind

              The results of the cloud gathering operation are merged with
              the current one.

            - C{byMethod}: the method named in the endpoint's C{method}
              attribute is invoked on the item with the current C{items}, 
              C{references} and C{cloudAlias} arguments. The method is
              supposed to return a list of items to include into the cloud
              and is supposed to fill the C{items} and C{references}
              dictionaries as this method does.

        @param item: the entrypoint of the cloud.
        @type item: an C{Item} instance
        @param items: an optional dictionary keyed on the item UUIDs that
        also receives all items in the cloud.
        @type items: dict
        @param references: an optional dictionary keyed on the item UUIDs
        that receives all items referenced from an endpoint with a C{byRef}
        include policy.
        @type references: dict
        @param cloudAlias: the optional alias name to use for C{byCloud}
        policy endpoints where the cloud is unspecified.
        @type cloudAlias: a string
        @return: the list of all items considered part of the cloud.
        """

        if not item.isItemOf(self.kind):
            raise TypeError, '%s (Kind: %s) is not of a kind this cloud (%s) understands' %(item.itsPath, item._kind.itsPath, self.itsPath)

        if items is None:
            items = {}
        if references is None:
            references = {}

        if not item.itsUUID in items:
            items[item.itsUUID] = item
            results = [item]
        else:
            results = []

        for alias, endpoint, inCloud in self.iterEndpoints(cloudAlias):
            if endpoint.includePolicy not in ('none', 'literal'):
                for other in endpoint.iterValues(item):
                    if other is not None and other.itsUUID not in items:
                        _items = endpoint.getItems(other, cloudAlias,
                                                   items, references, trace)
                        if trace is not None:
                            trace[(item, endpoint)] = _items
                        results.extend(_items)

        return results

    def getKeys(self, key, cloudAlias, keys=None, references=None, trace=None):

        if not self.kind.isKeyForInstance(key):
            raise TypeError, '%s (Kind: %s) is not of a kind this cloud (%s) understands' %(item.itsPath, item._kind.itsPath, self.itsPath)

        if keys is None:
            keys = set()
        if references is None:
            references = set()

        if not key in keys:
            keys.add(key)
            results = [key]
        else:
            results = []

        endpoints = [ep for x, ep, x in self.iterEndpoints(cloudAlias)
                     if ep.includePolicy not in ('none', 'literal')]
        pairs = [(ep.attribute[0], None) for ep in endpoints]

        for endpoint, firstValue in izip(endpoints,
                                         self.itsView.findValues(key, *pairs)):
            for other in endpoint.iterKeys(key, firstValue):
                if other is not None and other not in keys:
                    _keys = endpoint.getKeys(other, cloudAlias,
                                             keys, references, trace)
                    if trace is not None:
                        trace[(key, endpoint)] = _keys
                    results.extend(_keys)

        return results

    def copyItems(self, item, name=None, parent=None,
                  copies=None, cloudAlias=None):
        """
        Copy all items in the cloud.

        Items are first gathered as documented in L{getItems}. They are then
        copied as follows:

            - items in the result set returned by L{getItems} are copied and
              added to the result set copy in the order they occur in the
              original result set.

            - references to items in the original result set are copied as
              references to their corresponding copies and are set on the
              item copies everywhere they occur.

            - references to items in the C{references} dictionary upon
              returning from L{getItems}, that is, references to items that
              are not considered part of the cloud but are nonetheless
              referenced by items in it are set unchanged on the item copies
              everywhere they occur.

            - any other item references are not set on the item copies.

        The copy of the cloud entrypoint, C{item}, is first in the results
        list.
        
        @param item: the entry point of the cloud.
        @type item: an C{Item<chandlerdb.item.Item.Item>} instance
        @param parent: the optional parent of the copies; by default, each
        copy gets the same parent as the original
        @type parent: an C{Item<chandlerdb.item.Item.Item>} instance 
        @param copies: an optional dictionary keyed on the original item
        UUIDs that also received all items copies.
        @type copies: dict
        @param cloudAlias: the optional alias name to use for C{byCloud}
        policy endpoints where the cloud is unspecified.
        @type cloudAlias: a string
        @return: the list of all item copies considered part of the cloud.
        """

        items = {}
        references = {}
        copying = self.getItems(item, cloudAlias, items, references)
        
        if copies is None:
            copies = {}

        results = []
        def copyOther(copy, other, policy):
            if other is None:
                return None
            uuid = other.itsUUID
            if uuid in copies:
                return copies[uuid]
            if uuid in items:
                other = other.copy(None, parent, copies, 'remove',
                                   None, copyOther)
                results.append(other)
                return other
            if uuid in references:
                return other
            return Nil

        copy = item.copy(name, parent, copies, 'remove', None, copyOther)
        results.insert(0, copy)

        for item in copying:
            if item._uuid not in copies:
                results.append(item.copy(None, parent, copies, 'remove',
                                         None, copyOther))
                
        return results

    def deleteItems(self, item, recursive=False, cloudAlias=None):
        """
        Delete all items in the cloud.

        Items are first gathered as documented in L{getItems}. They are then
        deleted as follows:

            - items in the result set returned by L{getItems} are deleted.

            - references to items in the C{references} dictionary upon
              returning from L{getItems}, that is, references to items that
              are not considered part of the cloud but are nonetheless
              referenced by items in it are removed.

        It is an error to delete an item with children unless C{recursive}
        is set to C{True}.

        @param item: the entry point of the cloud.
        @type item: an C{Item<chandlerdb.item.Item.Item>} instance
        @param recursive: C{True} to recursively delete the items' children
        too, C{False} otherwise (the default).
        @type recursive: boolean
        @param cloudAlias: the optional alias name to use for C{byCloud}
        policy endpoints where the cloud is unspecified.
        @type cloudAlias: a string
        @return: the list of all item copies considered part of the cloud.
        """

        items = {}
        references = {}
        deleting = self.getItems(item, cloudAlias, items, references)

        def deleteItem(item):
            if not (item.isDeleted() or item.isDeleting()):
                if recursive:
                    item.delete(recursive=True, deletePolicy='remove')
                else:
                    if item.hasChildren():
                        for child in item.iterChildren():
                            if child._uuid in items:
                                deleteItem(child)
                            else:
                                raise RecursiveDeleteError, item
                    item.delete(deletePolicy='remove')

        for item in deleting:
            deleteItem(item)

    def getAttributeEndpoints(self, attrName, index=0, cloudAlias=None):

        endpoints = []
        for alias, endpoint, inCloud in self.iterEndpoints(cloudAlias):
            names = endpoint.attribute
            if index < len(names) and names[index] == attrName:
                endpoints.append(endpoint)

        return endpoints

    def iterEndpoints(self, cloudAlias=None):
        """
        Iterate over the endpoints of this cloud.

        If C{cloudAlias} is not C{None}, endpoints are inherited vertically
        by going up the cloud kind's superKind chain and horizontally by
        iterating over the cloud kind's superKinds.

        The iterator yields C{(alias, endpoint, inCloud)} tuples, where:

            - C{alias} is the alias of the endpoint in {cloud}'s
              C{endpoints} ref collection.

            - C{endpoint} is an C{Endpoint<chandlerdb.schema.Cloud.Endpoint>}
              instance.

            - C{inCloud} is the cloud C{endpoint} is defined on.

        If an endpoint is aliased in a cloud's endpoints collection,
        endpoints by the same alias are not inherited.
        """

        endpoints = self.getAttributeValue('endpoints', self._references,
                                           None, None)
        if endpoints is not None:
            for endpoint in endpoints:
                yield (endpoints.getAlias(endpoint), endpoint, self)

        if cloudAlias is not None:
            for superKind in self.kind.superKinds:
                for cloud in superKind.getClouds(cloudAlias):
                    for (alias, endpoint,
                         inCloud) in cloud.iterEndpoints(cloudAlias):
                        if (alias is None or
                            endpoints is None or
                            endpoints.resolveAlias(alias) is None):
                            yield (alias, endpoint, inCloud)

    def getEndpoints(self, alias, cloudAlias=None):
        """
        Get the endpoints for a given alias for this cloud.

        If C{cloudAlias} is not C{None} and this cloud does not define an
        endpoint by this alias, matching endpoints are inherited
        from the cloud kind's superKinds.

        @param alias: the alias of the endpoint(s) sought
        @type alias: a string
        @param cloudAlias: the optional cloud alias to inherit endpoints with
        @type cloudAlias: a string
        """

        if 'endpoints' in self._references:
            endpoint = self.endpoints.getByAlias(alias)
            if endpoint is not None:
                return [endpoint]

        if cloudAlias is not None:
            results = []
            for superKind in self.kind.superKinds:
                for cloud in superKind.getClouds(cloudAlias):
                    results.extend(cloud.getEndpoints(cloudAlias, alias))
            return results

        return []

    def iterEndpointValues(self, item, alias, cloudAlias=None):
        """
        Iterate over the items at the endpoints for the given alias.

        If C{cloudAlias} is not None and this cloud does not define an
        endpoint by this alias, matching endpoints are inherited
        from the cloud kind's superKinds.

        @param alias: the alias of the endpoint(s) sought
        @type alias: a string
        @param cloudAlias: the optional cloud alias to inherit endpoints with
        @type cloudAlias: a string
        """

        if not item.isItemOf(self.kind):
            raise TypeError, '%s (Kind: %s) is not of a kind this cloud (%s) understands' %(item.itsPath, item._kind.itsPath, self.itsPath)

        for endpoint in self.getEndpoints(alias, cloudAlias):
            for other in endpoint.iterValues(item):
                yield other

    def traceItem(self, item, trace, indent=0, done=None):

        if done is None:
            done = set()
        elif item in done:
            return

        done.add(item)
        for (other, endpoint), others in trace.iteritems():
            if item in others:
                yield (item, other, '.'.join(endpoint.attribute),
                       endpoint.includePolicy, indent)
                for tuple in self.traceItem(other, trace, indent + 1, done):
                    yield tuple


class Endpoint(Item):

    def getItems(self, item, cloudAlias, items, references, trace):

        policy = self.includePolicy
        results = []

        if policy == 'byValue':
            if not item.itsUUID in items:
                items[item.itsUUID] = item
                results.append(item)

        elif policy == 'byRef':
            references[item.itsUUID] = item

        elif policy == 'byCloud':
            def getItems(cloud):
                results.extend(cloud.getItems(item, cloudAlias,
                                              items, references, trace))

            cloud = self.getAttributeValue('cloud', self._references,
                                           None, None)
            if cloud is not None:
                getItems(cloud)
            else:
                kind = item.itsKind
                if cloudAlias is None:
                    cloudAlias = getattr(self, 'cloudAlias', None)
                clouds = kind.getClouds(cloudAlias)
                for cloud in clouds:
                    getItems(cloud)

        elif policy == 'byMethod':
            results.extend(getattr(item, self.method)(items, references,
                                                      cloudAlias))

        elif policy == 'none':
            pass

        else:
            raise NotImplementedError, policy

        return results

    def getKeys(self, key, cloudAlias, keys, references, trace):

        policy = self.includePolicy
        results = []

        if policy == 'byValue':
            if not key in keys:
                keys.add(key)
                results.append(key)

        elif policy == 'byRef':
            references.add(key)

        elif policy == 'byCloud':
            def getKeys(cloud):
                results.extend(cloud.getKeys(key, cloudAlias,
                                             keys, references, trace))

            cloud = self.getAttributeValue('cloud', self._references,
                                           None, None)
            if cloud is not None:
                getKeys(cloud)
            else:
                kind = self.itsView.kindForKey(key)
                if cloudAlias is None:
                    cloudAlias = getattr(self, 'cloudAlias', None)
                clouds = kind.getClouds(cloudAlias)
                for cloud in clouds:
                    getKeys(cloud)

        elif policy == 'byMethod':
            results.extend(getattr(self.itsView[key],
                                   self.method)(keys, references, cloudAlias))

        elif policy == 'none':
            pass

        else:
            raise NotImplementedError, policy

        return results

    def iterValues(self, item):

        def append(values, value):
            if not (value is None or isitemref(value)):
                if isitem(value) or isinstance(value, RefList):
                    values.append(value)
                elif isinstance(value, PersistentCollection):
                    values.append(value._iterItems())
                elif isinstance(value, AbstractSet):
                    values.append(value)
                else:
                    raise TypeError, type(value)

        value = item
        for name in self.attribute:
            if isinstance(value, PersistentCollection):
                values = []
                for v in value._iterItems():
                    append(values, v.getAttributeValue(name, None, None, None))
                value = values
            elif isinstance(value, RefList):
                values = []
                for v in value:
                    append(values, v.getAttributeValue(name, None, None, None))
                value = values
            elif isinstance(value, AbstractSet):
                values = []
                for v in value:
                    append(values, v.getAttributeValue(name, None, None, None))
                value = values
            elif isinstance(value, list):
                values = []
                for v in value:
                    if isitem(v):
                        append(values, v.getAttributeValue(name, None, None, None))
                    else:
                        for i in v:
                            append(values, i.getAttributeValue(name, None, None, None))
                value = values
            else:
                value = value.getAttributeValue(name, None, None, None)
                if value is None or isitemref(value):
                    break
                if not (isitem(value) or
                        isinstance(value, (PersistentCollection,
                                           RefList, AbstractSet))):
                    value = None
                    break

        if value is None:
            return []

        if isitem(value):
            return [value]

        if isinstance(value, PersistentCollection):
            return value._iterItems()

        return value

    def iterKeys(self, key, firstValue=Default):

        view = self.itsView

        def append(values, value):
            if value is not None:
                if isuuid(value) or isinstance(value, RefList):
                    values.append(value)
                elif isitem(value) or isitemref(value):
                    values.append(value.itsUUID)
                elif isinstance(value, PersistentCollection):
                    values.extend(value._iterKeys())
                elif isinstance(value, AbstractSet):
                    values.append(value)
                else:
                    raise TypeError, type(value)

        if firstValue is not Default:
            names = self.attribute[1:]
            value = firstValue
        else:
            names = self.attribute
            value = key

        for name in names:
            if isinstance(value, PersistentCollection):
                values = []
                for v in value._iterKeys():
                    append(values, view.findValue(v, name, None))
                value = values
            elif isinstance(value, RefList):
                values = []
                for v in value.iterkeys():
                    append(values, view.findValue(v, name, None))
                value = values
            elif isinstance(value, AbstractSet):
                values = []
                for v in value.iterkeys():
                    append(values, view.findValue(v, name, None))
                value = values
            elif isinstance(value, list):
                values = []
                for v in value:
                    if isuuid(v):
                        append(values, view.findValue(v, name, None))
                    else:
                        for k in v.iterkeys():
                            append(values, view.findValue(k, name, None))
                value = values
            else:
                value = view.findValue(value, name, None)
                if value is None:
                    break
                if isitemref(value) or isitem(value):
                    value = value.itsUUID
                elif not (isuuid(value) or
                          isinstance(value, (PersistentCollection,
                                             RefList, AbstractSet))):
                    value = None
                    break

        if value is None:
            return []

        if isuuid(value):
            return [value]

        if isitemref(value) or isitem(value):
            return [value.itsUUID]

        if isinstance(value, PersistentCollection):
            return value._iterKeys()

        if isinstance(value, RefList):
            return value.iterkeys()

        return value
