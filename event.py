from dataclasses import dataclass, field, asdict
import re


class Event:
    @staticmethod
    def from_id(event_id, *args):
        return event_classes[event_id](*args)

    def serialize_for(self, player):
        def try_serialize(value):
            if hasattr(value, 'serialize_for'):
                return value.serialize_for(player)
            elif hasattr(value, 'serialize'):
                return value.serialize()
            elif isinstance(value, list):
                return [try_serialize(x) for x in value]
            else:
                return str(value)
        d = {'event_id': self.__class__.__name__}
        d.update({
            key: try_serialize(value) for key, value in self.__dict__.items()})
        return d

    def __str__(self):
        return f'{self.__class__.__name__}({", ".join(map(str, self.__dict__.values()))})'

event_classes = {}

def event_id(event_id):
    def klass(klass):
        klass.event_id = event_id
        event_classes[event_id] = klass
        return klass
    return klass

@event_id('question')
@dataclass(repr=False)
class  QuestionEvent(Event):
    question: object

@event_id('pay_energy')
@dataclass(repr=False)
class PayEnergyEvent(Event):
    player: object
    energy: object
    new_total: object = None

@event_id('add_energy')
@dataclass(repr=False)
class AddEnergyEvent(Event):
    player: object
    energy: object
    new_total: object = None

@event_id('draw_card')
@dataclass(repr=False)
class DrawCardEvent(Event):
    player: object
    card: object
    card_id: str

    def serialize_for(self, player):
        d = {'event_id': self.__class__.__name__,
             'player': self.player.serialize_for(player)}
        if self.player is player:
            d['card'] = self.card.serialize_for(player)
        else:
            d['card_id'] = self.card_id
        return d

@event_id('draw_empty')
@dataclass(repr=False)
class DrawEmptyEvent(Event):
    player: object

@event_id('shuffle_library')
@dataclass(repr=False)
class ShuffleLibraryEvent(Event):
    player: object

@event_id('step')
@dataclass(repr=False)
class StepEvent(Event):
    step: object
    active_player: object

@event_id('clear_pool')
@dataclass(repr=False)
class ClearPoolEvent(Event):
    player: object

@event_id('priority')
@dataclass(repr=False)
class PriorityEvent(Event):
    player: object

@event_id('passed')
@dataclass(repr=False)
class PassedEvent(Event):
    player: object

@event_id('enter_the_battlefield')
@dataclass(repr=False)
class EnterTheBattlefieldEvent(Event):
    card: object
    controller: object
    perm_id: str

@event_id('exit_the_battlefield')
@dataclass(repr=False)
class ExitTheBattlefieldEvent(Event):
    permanent: object

@event_id('put_in_graveyard')
@dataclass(repr=False)
class PutInGraveyardEvent(Event):
    card: object

@event_id('play_source')
@dataclass(repr=False)
class PlaySourceEvent(Event):
    player: object
    card: object

@event_id('cast_spell')
@dataclass(repr=False)
class CastSpellEvent(Event):
    player: object
    card: object

@event_id('activate_ability')
@dataclass(repr=False)
class ActivateAbilityEvent(Event):
    aos_id: str
    permanent: object
    ability: object

@event_id('resolve_tos')
@dataclass(repr=False)
class ResolveEvent(Event):
    tos: object

@event_id('untap')
@dataclass(repr=False)
class UntapEvent(Event):
    permanent: object

@event_id('tap')
@dataclass(repr=False)
class TapEvent(Event):
    permanent: object

@event_id('reset_pass')
@dataclass(repr=False)
class ResetPassEvent(Event):
    pass

@event_id('attack')
@dataclass(repr=False)
class AttackEvent(Event):
    attacker: object
    player: object

@event_id('block')
@dataclass(repr=False)
class BlockEvent(Event):
    attacker: object
    blockers: list

@event_id('damage')
@dataclass(repr=False)
class DamageEvent(Event):
    permanent: object
    damage: object

@event_id('player_damage')
@dataclass(repr=False)
class PlayerDamageEvent(Event):
    player: object
    damage: object
    new_total: int = None

@event_id('remove_from_combat')
@dataclass(repr=False)
class RemoveFromCombatEvent(Event):
    permanent: object

@event_id('discard')
@dataclass(repr=False)
class DiscardEvent(Event):
    card: object

@event_id('lose')
@dataclass(repr=False)
class PlayerLosesEvent(Event):
    player: object
