import sys
import traceback
import pdb

from state import setup_duel, game_events
from dummy_deck import TEST_DECK
from aiplayers import random_answer


sys.setrecursionlimit(50)

def run_game(game):
    event_stream = game_events(game)
    for event in event_stream:
        game.handle(event)
        if game.question:
            player = game.question.player
            answer = random_answer(game.question)
            ret = game.set_answer(player, answer)
            assert ret, 'random answer is not valid'
            game.question = None
    print(f'Game produced {len(game.event_log)} events')

try:
    import state
    state.print = lambda *a, **b: None
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    run_game(game)
except:
    traceback.print_exc()
    pdb.post_mortem()
