import itertools
import random


class Namespace(dict):
    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__


def random_id(length=16):
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz')
                   for _ in range(length))


def unique_identifiers():
    for number in itertools.count():
        yield f'{number:04d}{random_id(6)}'
