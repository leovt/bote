class Namespace(dict):
    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__

import random

def random_id():
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz')
                   for _ in range(16))
