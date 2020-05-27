from dataclasses import dataclass, field, asdict

import energy
from step import STEP
from event import Event, PayEnergyEvent, TapEvent, ExitTheBattlefieldEvent, PutInGraveyardEvent, DamageEvent, PlayerDamageEvent

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

        yield PayEnergyEvent(player.name, self.energy)

    def __str__(self):
        return str(self.energy)

class TapCost:
    def can_pay(self, permanent, card):
        if not permanent:
            return False
        if permanent.tapped:
            return False
        if 'creature' in permanent.types:
            if not permanent.has('haste'):
                if not permanent.on_battlefield_at_begin_of_turn:
                    return False
        return True

    def pay(self, permanent, card):
        yield TapEvent(permanent.perm_id)

    def __str__(self):
        return '{T}'

@dataclass
class ActivatableAbility:
    cost: list
    effect: object
    is_energy_ability: bool=False

    def __str__(self):
        return '%s: activate ability' % ', '.join(str(x) for x in self.cost)

    def serialize_for(self, player):
        return {}

@dataclass
class TriggeredAbility:
    trigger: object
    effect: object

    def __str__(self):
        return 'triggered ability'

    def serialize_for(self, player):
        return {}


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


def parse_trigger(string):
    tokens = string.split()
    if tokens[0] == 'BEGIN_OF_STEP':
        return tokens[0], STEP[tokens[1]]
    assert False, 'Unknown trigger %r' % string
