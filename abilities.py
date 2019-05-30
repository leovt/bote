from dataclasses import dataclass, field

import energy

from event import Event

class EnergyCost:
    def __init__(self, energy):
        self.energy = energy

    def can_pay(self, permanent, card):
        if permanent:
            player = permanent.controller
        else:
            player = card.owner

        return player.energy_pool.can_pay(self.energy)

    def pay(self, permanent, card):
        if permanent:
            player = permanent.controller
        else:
            player = card.owner

        yield Event('pay_energy', player, self.energy)

    def __str__(self):
        return str(self.energy)

class TapCost:
    def can_pay(self, permanent, card):
        return permanent and not permanent.tapped

    def pay(self, permanent, card):
        yield Event('tap', permanent)

    def __str__(self):
        return '{T}'

@dataclass
class ActivatableAbility:
    cost: list
    effect: object
    is_energy_ability: bool=False

    def __str__(self):
        return '%s: activate ability' % ', '.join(str(x) for x in self.cost)

def parse_cost(string):
    components = string.split(',')
    cost = []
    for c in components:
        c = c.strip()
        if c == '{T}':
            cost.append(TapCost())
        elif energy.Energy.parse(c) is not None:
            cost.append(EnergyCost(energy.Energy.parse(c)))
        else:
            assert False
    return cost

def parse_effect(string):
    def _effect(controller):
        for line in string.splitlines():
            tokens = line.split()
            args = []
            for token in tokens:
                if token == '$controller':
                    args.append(controller)
                elif energy.Energy.parse(token):
                    args.append(energy.Energy.parse(token))
                else:
                    args.append(token)
            yield Event(*args)
    return _effect
