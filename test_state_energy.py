import unittest

from cards import ArtCard, Card
from energy import BLUE, GREEN, RED
from event import ClearPoolEvent, StepEvent, event_classes
from effects import Effect, EffectTemplate
from state import Game, Player, check_triggers, play_source, turn_based_actions
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


if __name__ == '__main__':
    unittest.main()
