import sys
import traceback
import pdb

from state import setup_duel, game_events
from dummy_deck import TEST_DECK
from aiplayers import random_answer


sys.setrecursionlimit(50)

def run_game():
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    game.run()
    while True:
        question = game.next_decision()
        if not question:
            break

        answer = random_answer(question)
        ret = game.set_answer(question.player, answer)
        assert ret, 'random answer is not valid'
        game.question = None
    print(f'Game produced {len(game.event_log)} events, next id is {next(game.unique_ids)}.')


if __name__ == '__main__':
    try:
        import state
        state.print = lambda *a, **b: None
        run_game()
    except:
        traceback.print_exc()
        pdb.post_mortem()
