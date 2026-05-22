from event import (EndContinuousEffectEvent,
                   EndTriggerEvent,
                   ExitTheBattlefieldEvent,
                   PutInGraveyardEvent)


def put_in_graveyard_events(game, permanent):
    yield ExitTheBattlefieldEvent(permanent.perm_id)
    for effect_id in list(game.continuous_effects.keys_by_perm_id(permanent.perm_id)):
        yield EndContinuousEffectEvent(effect_id)
    for trigger_id in list(game.triggered_effects.keys_by_perm_id(permanent.perm_id)):
        yield EndTriggerEvent(trigger_id)
    if hasattr(permanent.card, 'secret_id'):
        yield PutInGraveyardEvent(permanent.card.secret_id)
    else:
        assert permanent.card.token
