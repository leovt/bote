import random
from cards import Card, ArtCard

class Library:
    def __init__(self, contents):
        self.random_part = list(contents)
        self.known_top = []
        self.known_bottom = []

    def shuffle(self):
        self.random_part.extend(self.known_top)
        self.random_part.extend(self.known_bottom)
        self.known_top.clear()
        self.known_bottom.clear()

    def __len__(self):
        return len(self.random_part) + len(self.known_top) + len(self.known_bottom)

    def __iter__(self):
        yield from self.known_top
        yield from self.random_part
        yield from self.known_bottom

    def top(self):
        if self.known_top:
            return self.known_top[-1]
        elif self.random_part:
            index = random.randrange(len(self.random_part))
            element = self.random_part.pop(index)
            self.known_top.append(element)
            return element
        else:
            return self.known_bottom[-1]

    def pop(self):
        if self.known_top:
            return self.known_top.pop()
        elif self.random_part:
            index = random.randrange(len(self.random_part))
            return self.random_part.pop(index)
        else:
            return self.known_bottom.pop()

    def pop_given(self, item):
        '''pop top item from library and verify it is identical to the given item.
           in case the top item is unknown (shuffled) verify it is possible to draw given item.
        '''
        if self.known_top:
            if item == self.known_top[-1]:
                return self.known_top.pop()
            else:
                raise ValueError('Library.pop_given: given item does not match top')
        elif self.random_part:
            index = self.random_part.index(item)
            return self.random_part.pop(index)
        else:
            if item == self.known_bottom[-1]:
                return self.known_bottom.pop()
            else:
                raise ValueError('Library.pop_given: given item does not match top')


def make_library(deck, player):
    cards = [Card(ArtCard.get_by_id(art_id), player)
             for art_id, count in deck.items()
             for _ in range(count)
            ]
    return Library(cards)
