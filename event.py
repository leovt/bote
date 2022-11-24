from typing import Union, Literal
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict

_event_classes = []
def _register(klass):
    _event_classes.append(klass)
    return klass

@_register
class QuestionEvent(BaseModel):
    event_type: Literal['question']
    question: object

@_register
class PayEnergyEvent(BaseModel):
    event_type: Literal['pay_energy']
    player_id: str
    energy: object
    new_total: object = None

@_register
class AddEnergyEvent(BaseModel):
    event_type: Literal['add_energy']
    player_id: str
    energy: object
    new_total: object = None

@_register
class CreatePlayerEvent(BaseModel):
    event_type: Literal['create_player']
    player_id: str
    name: str
    cards: list
    next_in_turn_id: str

@_register
class DrawCardEvent(BaseModel):
    event_type: Literal['draw_card']
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

@_register
class DrawEmptyEvent(BaseModel):
    event_type: Literal['draw_empty']
    player_id: str

@_register
class ShuffleLibraryEvent(BaseModel):
    event_type: Literal['shuffle_library']
    player_id: str

@_register
class StepEvent(BaseModel):
    event_type: Literal['step']
    step: str
    active_player_id: str

@_register
class ClearPoolEvent(BaseModel):
    event_type: Literal['clear_pool']
    player_id: str

@_register
class PriorityEvent(BaseModel):
    event_type: Literal['priority']
    player_id: str

@_register
class PassedEvent(BaseModel):
    event_type: Literal['passed']
    player_id: str

@_register
class EnterTheBattlefieldEvent(BaseModel):
    event_type: Literal['enter_the_battlefield']
    card_secret_id: str
    art_id: str
    controller_id: str
    perm_id: str
    choices: dict

@_register
class ExitTheBattlefieldEvent(BaseModel):
    event_type: Literal['exit_the_battlefield']
    perm_id: str

@_register
class PutInGraveyardEvent(BaseModel):
    event_type: Literal['put_in_graveyard']
    card_secret_id: str

@_register
class PlaySourceEvent(BaseModel):
    event_type: Literal['play_source']
    player_id: str
    card_secret_id: str

@_register
class CastSpellEvent(BaseModel):
    event_type: Literal['cast_spell']
    stack_id: str
    player_id: str
    card_secret_id: str
    target: str = None

@_register
class ActivateAbilityEvent(BaseModel):
    event_type: Literal['activate_ability']
    stack_id: str
    perm_id: str
    ability_index: int
    choices: dict

@_register
class StackEffectEvent(BaseModel):
    event_type: Literal['stack_effect']
    stack_id: str
    perm_id: str
    effect: object
    choices: dict

@_register
class CreateTriggerEvent(BaseModel):
    event_type: Literal['create_trigger']
    trigger_id: str
    perm_id: str or None
    trigger: list
    effect: object

@_register
class EndTriggerEvent(BaseModel):
    event_type: Literal['end_trigger']
    trigger_id: str

@_register
class CreateContinuousEffectEvent(BaseModel):
    event_type: Literal['create_continuous_effect']
    effect_id: str
    perm_id: str or None
    object_ids: list
    modifiers: list
    until_end_of_turn: bool

@_register
class EndContinuousEffectEvent(BaseModel):
    event_type: Literal['end_continuous_effect']
    effect_id: str

@_register
class ResolveEvent(BaseModel):
    event_type: Literal['resolve_tos']
    stack_id: str

@_register
class UntapEvent(BaseModel):
    event_type: Literal['untap']
    perm_id: str

@_register
class TapEvent(BaseModel):
    event_type: Literal['tap']
    perm_id: str

@_register
class ResetPassEvent(BaseModel):
    event_type: Literal['reset_pass']

@_register
class AttackEvent(BaseModel):
    event_type: Literal['attack']
    attacker_id: str
    player_id: str

@_register
class BlockEvent(BaseModel):
    event_type: Literal['block']
    attacker_id: object
    blocker_ids: list

@_register
class DamageEvent(BaseModel):
    event_type: Literal['damage']
    perm_id: str
    damage: object

@_register
class PlayerDamageEvent(BaseModel):
    event_type: Literal['player_damage']
    player_id: str
    damage: object
    new_total: int = None

@_register
class RemoveFromCombatEvent(BaseModel):
    event_type: Literal['remove_from_combat']
    perm_id: str

@_register
class DiscardEvent(BaseModel):
    event_type: Literal['discard']
    card_secret_id: str

@_register
class PlayerLosesEvent(BaseModel):
    event_type: Literal['lose']
    player_id: str

@_register
class ClearTriggerEvent(BaseModel):
    event_type: Literal['clear_trigger']

@_register
class ClearDamageEvent(BaseModel):
    event_type: Literal['clear_damage']


@_register
class Event(BaseModel):
    event: Union[tuple(_event_classes)] = Field(discriminator='event_type')

if __name__ == '__main__':
    print(Event.schema_json(indent=4))