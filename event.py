from dataclasses import dataclass, asdict

class Event:
    @staticmethod
    def from_id(event_id, *args):
        return event_classes[event_id](*args)

    def serialize_for(self, player, game):
        def serialize_field(key, value):
            if 'player_id' in key or 'controller_id' in key or 'owner_id' in key:
                if value is None:
                    return key[:-3], None
                return key[:-3], game.players[value].serialize_for(player)
            elif 'card_secret_id' == key:
                if value is not None:
                    return 'card', game.cards[value].serialize_for(player)
                else:
                    return None, None
            elif 'energy' == key:
                return key, str(value)
            elif isinstance(value, (int, str, type(None))):
                return key, value
            elif hasattr(value, 'serialize_for'):
                return key, value.serialize_for(player)
            elif hasattr(value, 'serialize'):
                return key, value.serialize()
            else:
                return key, value
        d = {'event_id': self.__class__.__name__}
        for key, value in self.__dict__.items():
            nkey, nvalue = serialize_field(key, value)
            if nkey:
                d[nkey] = nvalue
        assert 'card_secret_id' not in d
        return d

    def serialize(self):
        d = {'event_id': self.event_id}
        d.update(asdict(self))
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
    player_id: str
    energy: object
    new_total: object = None

@event_id('add_energy')
@dataclass(repr=False)
class AddEnergyEvent(Event):
    player_id: str
    energy: object
    new_total: object = None

@event_id('create_player')
@dataclass(repr=False)
class CreatePlayerEvent(Event):
    player_id: str
    name: str
    cards: list
    next_in_turn_id: str

@event_id('draw_card')
@dataclass(repr=False)
class DrawCardEvent(Event):
    player_id: str
    card_secret_id: str
    card_id: str

    def serialize_for(self, player, game):
        d = {'event_id': self.__class__.__name__,
             'player': game.players[self.player_id].serialize_for(player)}
        if self.player_id == player.player_id:
            d['card'] = game.cards[self.card_secret_id].serialize_for(player)
        else:
            d['card_id'] = self.card_id
        return d

@event_id('draw_empty')
@dataclass(repr=False)
class DrawEmptyEvent(Event):
    player_id: str

@event_id('shuffle_library')
@dataclass(repr=False)
class ShuffleLibraryEvent(Event):
    player_id: str

@event_id('step')
@dataclass(repr=False)
class StepEvent(Event):
    step: str
    active_player_id: str

@event_id('clear_pool')
@dataclass(repr=False)
class ClearPoolEvent(Event):
    player_id: str

@event_id('priority')
@dataclass(repr=False)
class PriorityEvent(Event):
    player_id: str

@event_id('passed')
@dataclass(repr=False)
class PassedEvent(Event):
    player_id: str

@event_id('enter_the_battlefield')
@dataclass(repr=False)
class EnterTheBattlefieldEvent(Event):
    card_secret_id: str
    art_id: str
    controller_id: str
    perm_id: str
    choices: dict

@event_id('exit_the_battlefield')
@dataclass(repr=False)
class ExitTheBattlefieldEvent(Event):
    perm_id: str

@event_id('put_in_graveyard')
@dataclass(repr=False)
class PutInGraveyardEvent(Event):
    card_secret_id: str

@event_id('play_source')
@dataclass(repr=False)
class PlaySourceEvent(Event):
    player_id: str
    card_secret_id: str

@event_id('cast_spell')
@dataclass(repr=False)
class CastSpellEvent(Event):
    stack_id: str
    player_id: str
    card_secret_id: str
    target: str = None

@event_id('activate_ability')
@dataclass(repr=False)
class ActivateAbilityEvent(Event):
    stack_id: str
    perm_id: str
    ability_index: int
    choices: dict

@event_id('create_continuous_effect')
@dataclass(repr=False)
class CreateContinuousEffectEvent(Event):
    effect_id: str
    perm_id: str or None
    object_ids: list
    modifiers: list
    until_end_of_turn: bool

@event_id('create_continuous_effect')
@dataclass(repr=False)
class EndContinuousEffectEvent(Event):
    effect_id: str

@event_id('resolve_tos')
@dataclass(repr=False)
class ResolveEvent(Event):
    stack_id: str

@event_id('untap')
@dataclass(repr=False)
class UntapEvent(Event):
    perm_id: str

@event_id('tap')
@dataclass(repr=False)
class TapEvent(Event):
    perm_id: str

@event_id('reset_pass')
@dataclass(repr=False)
class ResetPassEvent(Event):
    pass

@event_id('attack')
@dataclass(repr=False)
class AttackEvent(Event):
    attacker_id: str
    player_id: str

@event_id('block')
@dataclass(repr=False)
class BlockEvent(Event):
    attacker_id: object
    blocker_ids: list

@event_id('damage')
@dataclass(repr=False)
class DamageEvent(Event):
    perm_id: str
    damage: object

@event_id('player_damage')
@dataclass(repr=False)
class PlayerDamageEvent(Event):
    player_id: str
    damage: object
    new_total: int = None

@event_id('remove_from_combat')
@dataclass(repr=False)
class RemoveFromCombatEvent(Event):
    perm_id: str

@event_id('discard')
@dataclass(repr=False)
class DiscardEvent(Event):
    card_secret_id: str

@event_id('lose')
@dataclass(repr=False)
class PlayerLosesEvent(Event):
    player_id: str

@event_id('clear_trigger')
@dataclass(repr=False)
class ClearTriggerEvent(Event):
    pass

@event_id('clear_damage')
@dataclass(repr=False)
class ClearDamageEvent(Event):
    pass
