import unittest

from energy import BLUE, GREEN, RED
from event import ClearPoolEvent, StepEvent
from state import Game, Player, end_of_step, turn_based_actions
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


if __name__ == '__main__':
    unittest.main()
