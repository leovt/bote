from dataclasses import dataclass, field

import energy

from event import Event, PayEnergyEvent, TapEvent

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
        return permanent and not permanent.tapped

    def pay(self, permanent, card):
        yield TapEvent(permanent)

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
            yield Event.from_id(*args)
    return _effect


def describe_effect(script, lang):
    if lang not in ('en', 'de', 'ko'):
        lang = 'en'

    lines = []
    for line in script.splitlines():
        tokens = line.split()
        if tokens[0] == 'add_energy':
            if tokens[1] == '$controller':
                lines.append({
                    'en': f'Add {tokens[2]} to your energy pool.',
                    'de': f'Erhöhe deinen Energievorrat um {tokens[2]}.',
                    'ko': f'당신의 에너지 저장고에 {tokens[2]}를 덧붙이세요.',
                }[lang])
            elif tokens[1] == '$target_player':
                lines.append({
                    'en': f'Add {tokens[2]} to target players energy pool.',
                    'de': f'Erhöhe den Energievorrat eines Spielers deiner Wahl um {tokens[2]}.',
                    'ko': f'선택한 플레이어의 에너지 저장고에 {tokens[2]}를 덧붙이세요.',
                }[lang])
            else:
                assert False, f'bad argument {tokens[1]}.'
        elif tokens[0] == 'bury':
                assert tokens[1] == '$self'
                lines.append({
                    'en': f'Bury this creature',
                    'de': f'Begrabe diese Kreatur',
                    'ko': f'이생물이 죽어요',
                }[lang])
        else:
            assert False, f'Text for {tokens[0]} not implemented.'
    return ' '.join(lines)
