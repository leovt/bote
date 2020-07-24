"""This module implements specialized container datatypes for the BOTE project"""

from collections import OrderedDict, defaultdict


class IndexedOrderedCollection:
    """A collection maintaining order providing fast access by some attributes

    Each inserted value must have the following members which will be indexed:
        - object_ids: each object_id in this iterable will be indexed
        - until_end_of_turn: bool
    These indexed members must not be modified while the value is in the collection
    """

    def __init__(self):
        self._table = OrderedDict()
        self._index = defaultdict(OrderedDict)
        self._until_end_of_turn = OrderedDict()
        self._from_permanent = defaultdict(OrderedDict)

    def __setitem__(self, key, value):
        if key in self._table:
            del self[key]
        self._table[key] = value

        for object_id in value.object_ids:
            self._index[object_id][key] = value

        if value.until_end_of_turn:
            self._until_end_of_turn[key] = value

        if value.perm_id:
            self._from_permanent[value.perm_id][key] = value

    def __getitem__(self, key):
        return self._table[key]

    def __delitem__(self, key):
        value = self._table.pop(key)

        for object_id in value.object_ids:
            del self._index[object_id][key]
            if not self._index[object_id]:
                del self._index[object_id]

        if value.until_end_of_turn:
            del self._until_end_of_turn[key]

        if value.perm_id:
            del self._from_permanent[value.perm_id][key]
            if not self._from_permanent[value.perm_id]:
                del self._from_permanent[value.perm_id]

    def keys(self):
        return self._table.keys()

    def values(self):
        return self._table.values()

    def values_by_object_id(self, object_id):
        """return the values in the collection referencing the given object_id"""
        return self._index[object_id].values()

    def keys_by_object_id(self, object_id):
        """return the keys of all values in the collection referencing the given object_id"""
        return self._index[object_id].keys()

    def values_until_end_of_turn(self):
        """return a list of all values which are marked until_end_of_turn"""
        return self._until_end_of_turn.values()

    def keys_until_end_of_turn(self):
        """return the keys of all values which are marked until_end_of_turn"""
        return self._until_end_of_turn.keys()

    def values_by_perm_id(self, perm_id):
        """return the values in the collection originating from the given permanent"""
        return self._from_permanent[perm_id].values()

    def keys_by_perm_id(self, perm_id):
        """return the keys of all values in the collection originating from the given permanent"""
        return self._from_permanent[perm_id].keys()


class TriggerCollection:
    """A collection maintaining order providing fast access by some attributes

    Each inserted value must have the following members which will be indexed:
        - object_ids: each object_id in this iterable will be indexed
        - until_end_of_turn: bool
    These indexed members must not be modified while the value is in the collection
    """

    def __init__(self):
        self._table = OrderedDict()
        self._from_permanent = defaultdict(OrderedDict)

    def __setitem__(self, key, value):
        if key in self._table:
            del self[key]
        self._table[key] = value

        if value.perm_id:
            self._from_permanent[value.perm_id][key] = value

    def __getitem__(self, key):
        return self._table[key]

    def __delitem__(self, key):
        value = self._table.pop(key)

        if value.perm_id:
            del self._from_permanent[value.perm_id][key]
            if not self._from_permanent[value.perm_id]:
                del self._from_permanent[value.perm_id]

    def keys(self):
        return self._table.keys()

    def values(self):
        return self._table.values()

    def values_by_perm_id(self, perm_id):
        """return the values in the collection originating from the given permanent"""
        return self._from_permanent[perm_id].values()

    def keys_by_perm_id(self, perm_id):
        """return the keys of all values in the collection originating from the given permanent"""
        return self._from_permanent[perm_id].keys()
