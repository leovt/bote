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

def add_energy_effect(energy):
    def _add_energy_effect(controller):
        yield Event('add_energy', controller, energy)
        controller.energy_pool.add(energy)
    return _add_energy_effect

firesource_ability = ActivatableAbility(
    cost = [TapCost()],
    effect = add_energy_effect(energy.RED),
    is_energy_ability = True
)
