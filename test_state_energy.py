import unittest

from cards import ArtCard, Card
from energy import BLUE, GREEN, RED
from event import (
    CastSpellEvent,
    ClearPoolEvent,
    EnterTheBattlefieldEvent,
    PutInGraveyardEvent,
    StepEvent,
    event_classes,
)
from effects import Effect, EffectTemplate
from state import Game, Player, Spell, check_triggers, play_source, turn_based_actions
from state import end_of_step
from step import STEP


def minimal_game(step=STEP.PRECOMBAT_MAIN):
    game = Game()
    player_one = Player(0, 'One', 1)
    player_two = Player(1, 'Two', 0)
    game.players[player_one.player_id] = player_one
    game.players[player_two.player_id] = player_two
    game.active_player = player_one
    game.step = step
    return game, player_one, player_two


def handle_all(game, events):
    for event in events:
        game.handle(event)


class TestEnergyDrainTiming(unittest.TestCase):
    def test_end_of_step_does_not_clear_energy(self):
        game, active_player, inactive_player = minimal_game()
        active_player.energy_pool.add(RED)
        inactive_player.energy_pool.add(BLUE)

        events = list(end_of_step(game))

        self.assertFalse(
            any(isinstance(event, ClearPoolEvent) for event in events))
        for event in events:
            game.handle(event)
        self.assertEqual(active_player.energy_pool.energy, RED)
        self.assertEqual(inactive_player.energy_pool.energy, BLUE)

    def test_untap_clears_active_player_energy_first(self):
        game, active_player, inactive_player = minimal_game(STEP.UNTAP)
        active_player.energy_pool.add(RED)
        inactive_player.energy_pool.add(BLUE)

        events = list(turn_based_actions(game))

        self.assertIsInstance(events[0], ClearPoolEvent)
        self.assertEqual(events[0].player_id, active_player.player_id)
        for event in events:
            game.handle(event)
        self.assertEqual(active_player.energy_pool.energy.total, 0)
        self.assertEqual(inactive_player.energy_pool.energy, BLUE)

    def test_next_player_untap_clears_only_that_player_energy(self):
        game, previous_player, active_player = minimal_game(STEP.UNTAP)
        game.active_player = active_player
        previous_player.energy_pool.add(GREEN)
        active_player.energy_pool.add(RED)

        events = list(turn_based_actions(game))

        self.assertEqual(events[0].player_id, active_player.player_id)
        for event in events:
            game.handle(event)
        self.assertEqual(previous_player.energy_pool.energy, GREEN)
        self.assertEqual(active_player.energy_pool.energy.total, 0)
        self.assertIsInstance(events[-1], StepEvent)
        self.assertEqual(events[-1].step, STEP.UPKEEP.name)

    def test_source_adds_energy_when_it_enters(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)

        handle_all(game, play_source(game, active_player, source))

        self.assertEqual(active_player.energy_pool.energy, RED)

    def test_source_adds_energy_after_turn_start_drain(self):
        game, active_player, _ = minimal_game(STEP.UNTAP)
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)

        handle_all(game, play_source(game, active_player, source))
        active_player.energy_pool.add(GREEN)

        game.handle(StepEvent(STEP.UNTAP.name, active_player.player_id))
        for event in turn_based_actions(game):
            game.handle(event)

        triggered_effects, stale_trigger_ids = check_triggers(game)
        self.assertEqual(stale_trigger_ids, [])
        triggered_effect = triggered_effects[0]
        self.assertEqual(triggered_effect.perm_id, next(iter(game.battlefield)).perm_id)
        for event_spec in triggered_effect.effect:
            kwargs = {
                key: value
                for key, value in event_spec.items()
                if key != 'event_id'
            }
            event = event_classes[event_spec['event_id']](**kwargs)
            game.handle(event)

        self.assertEqual(active_player.energy_pool.energy, RED)

    def test_destroy_effect_cleans_up_source_trigger(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)
        handle_all(game, play_source(game, active_player, source))
        permanent = next(iter(game.battlefield))
        self.assertTrue(list(game.triggered_effects.keys_by_perm_id(permanent.perm_id)))

        destroy = Effect(EffectTemplate.parse('destroy this'), game, {}, active_player, permanent)
        handle_all(game, destroy.execute())

        self.assertNotIn(permanent.perm_id, game.battlefield)
        self.assertFalse(list(game.triggered_effects.keys_by_perm_id(permanent.perm_id)))

    def test_stale_trigger_is_reported_for_cleanup(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)
        handle_all(game, play_source(game, active_player, source))
        permanent = next(iter(game.battlefield))
        trigger_id = next(iter(game.triggered_effects.keys_by_perm_id(permanent.perm_id)))
        del game.battlefield[permanent.perm_id]
        game.trigger(('BEGIN_OF_TURN', active_player.player_id))

        with self.assertLogs('state', level='WARNING') as captured:
            triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(triggered_effects, [])
        self.assertEqual(stale_trigger_ids, [trigger_id])
        self.assertIn('Removing stale trigger', captured.output[0])


class TestCastTriggers(unittest.TestCase):
    def install_pyroscientist(self, game, controller):
        card = Card('pyro-secret-id', ArtCard.get_by_id(11901), controller)
        game.cards[card.secret_id] = card
        game.handle(EnterTheBattlefieldEvent(
            card.secret_id, None, controller.player_id, 'pyro-permanent', {}))
        permanent = game.battlefield['pyro-permanent']
        for template in card.effect:
            handle_all(game, Effect(template, game, {}, controller, permanent).execute())
        return permanent

    def test_pyroscientist_registers_simple_cast_triggers(self):
        game, controller, _ = minimal_game()
        self.install_pyroscientist(game, controller)

        triggers = {
            event.trigger
            for event in game.triggered_effects.values()
        }
        self.assertEqual(triggers, {
            ('CAST', controller.player_id, ('instant',)),
            ('CAST', controller.player_id, ('sorcery',)),
        })

    def test_pyroscientist_triggers_only_for_matching_controller_cast(self):
        game, controller, opponent = minimal_game()
        self.install_pyroscientist(game, controller)
        instant = Card('instant-secret-id', ArtCard.get_by_id(11401), controller)
        game.cards[instant.secret_id] = instant
        controller.hand.add(instant)

        game.handle(CastSpellEvent(
            'instant-stack-id', controller.player_id, instant.secret_id, {}))
        triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(stale_trigger_ids, [])
        self.assertEqual(len(triggered_effects), 1)
        self.assertEqual(triggered_effects[0].effect[0]['art_id'], 90201)

        game.triggers.clear()
        opponent_instant = Card(
            'opponent-instant-secret-id', ArtCard.get_by_id(11401), opponent)
        game.cards[opponent_instant.secret_id] = opponent_instant
        opponent.hand.add(opponent_instant)
        game.handle(CastSpellEvent(
            'opponent-stack-id', opponent.player_id, opponent_instant.secret_id, {}))

        triggered_effects, _ = check_triggers(game)
        self.assertEqual(triggered_effects, [])

    def test_cast_trigger_unparses_as_canonical_rule_text(self):
        effect = EffectTemplate.parse(
            'when you cast any .instant: create 1 (90201) token')

        self.assertEqual(
            effect.unparse(),
            'when you cast any .instant: create 1 (90201) token',
        )


class TestContinuousEffectResolution(unittest.TestCase):
    def test_self_modifier_does_nothing_after_permanent_leaves(self):
        game, controller, _ = minimal_game()
        card = Card('creature-secret-id', ArtCard.get_by_id(10501), controller)
        game.cards[card.secret_id] = card
        game.handle(EnterTheBattlefieldEvent(
            card.secret_id, None, controller.player_id, 'creature-permanent', {}))
        permanent = game.battlefield['creature-permanent']
        modifier = Effect(
            EffectTemplate.parse('this has +1/+0 until end of turn'),
            game,
            {},
            controller,
            permanent,
        )

        del game.battlefield[permanent.perm_id]
        events = modifier.execute()

        self.assertEqual(events, [])
        self.assertEqual(list(game.continuous_effects.keys()), [])


class TestSpellResolution(unittest.TestCase):
    def test_targeted_spell_does_nothing_if_target_has_left(self):
        game, controller, _ = minimal_game()
        target_card = Card('target-secret-id', ArtCard.get_by_id(10501), controller)
        spell_card = Card('spell-secret-id', ArtCard.get_by_id(11401), controller)
        game.cards[target_card.secret_id] = target_card
        game.cards[spell_card.secret_id] = spell_card
        game.handle(EnterTheBattlefieldEvent(
            target_card.secret_id, None, controller.player_id, 'target-permanent', {}))
        spell = Spell(
            'spell-stack-id',
            controller,
            spell_card,
            {'@1': {'type': 'permanent', 'perm_id': 'target-permanent'}},
        )

        del game.battlefield['target-permanent']
        events = list(spell.resolve(game))

        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], PutInGraveyardEvent)
        handle_all(game, events)
        self.assertIn(spell_card, controller.graveyard)


if __name__ == '__main__':
    unittest.main()
