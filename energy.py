from operator import add, sub
import re

class Energy(tuple):
    def __new__(cls, total=None, red=0, yellow=0, blue=0, green=0, white=0, variable=0):
        if total is None:
            total = red + yellow + blue + green + white
        return tuple.__new__(cls, (total, red, yellow, blue, green, white, variable))

    @property
    def total(self):
        return self[0]

    @property
    def red(self):
        return self[1]

    @property
    def yellow(self):
        return self[2]

    @property
    def blue(self):
        return self[3]

    @property
    def green(self):
        return self[4]

    @property
    def white(self):
        return self[5]

    @property
    def variable(self):
        return self[6]

    def __add__(self, other):
        return Energy(*map(add, self, other))

    def __sub__(self, other):
        return Energy(*map(sub, self, other))

    def __mul__(self, other):
        return Energy(*(other * x for x in self))

    __rmul__ = __mul__

    def is_valid(self):
        return all(x>=0 for x in self)

    def decompose(self):
        colorless = self[0] - sum(self[1:])
        ret = []
        if colorless:
            ret.append(str(colorless))
        for letter, amount in zip('RYBGWX', self[1:]):
            ret.extend([letter]*amount)
        if not ret:
            ret.append(0)
        return ret

    def symbols(self):
        symbols = [
            (self.red, 'r'),
            (self.yellow, 'y'),
            (self.green, 'g'),
            (self.blue, 'b'),
            (self.white, 'w'),
        ]
        symbols.sort(reverse=True)
        symbols.append((self.total - self.red - self.green - self.yellow - self.blue - self.white, '1'))
        symbols.append((self.variable, 'x'))
        return ''.join(a*b for (a,b) in symbols)

    def replace_variable(self, x):
        values = list(self)
        values[0] += values[-1] * x
        values[-1] = 0
        return Energy(*values)

    def __str__(self):
        return ''.join('{%s}' % x for x in self.decompose())

    @staticmethod
    def parse(string):
        total = 0
        red = 0
        yellow = 0
        blue = 0
        green = 0
        white = 0
        variable = 0
        match = re.match(r'^(?:\{(\d+|[RYBGWX])\})+$', string)
        if not match:
            return None
        for group in re.findall(r'\{(\d+|[RYBGWX])\}', string):
            if group == 'R':
                red += 1
                total += 1
            elif group == 'Y':
                yellow += 1
                total += 1
            elif group == 'B':
                blue += 1
                total += 1
            elif group == 'G':
                green += 1
                total += 1
            elif group == 'W':
                white += 1
                total += 1
            elif group == 'X':
                variable += 1
            else:
                total += int(group)
        return Energy(total, red, yellow, blue, green, white, variable)





class EnergyPool:
    def __init__(self):
        self.energy = ZERO

    def can_pay(self, cost):
        print(self.energy, cost)
        return (self.energy - cost).is_valid()

    def pay(self, cost):
        if not self.can_pay(cost):
            raise ValueError('insufficient energy')
        self.energy -= cost

    def add(self, energy):
        self.energy += energy

    def clear(self):
        self.energy = ZERO

ZERO = Energy()
COLORLESS = Energy(total=1)
BLUE = Energy(blue=1)
WHITE = Energy(white=1)
GREEN = Energy(green=1)
RED = Energy(red=1)
YELLOW = Energy(yellow=1)
