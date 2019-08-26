import sys
import traceback
import pdb
import random

from state import setup_duel, game_events
from dummy_deck import TEST_DECK


sys.setrecursionlimit(50)


def run_game(game):
    event_stream = game_events(game)
    for event in event_stream:
        game.handle(event)
        if game.question:
            player = game.question.player

            if game.question.__class__.__name__ == "ChooseAction":
                ret = game.set_answer(player, random.randrange(len(game.question.choices)))
                assert ret, 'random answer is not valid'

            elif game.question.__class__.__name__ == "DeclareAttackers":
                if not game.question.choices:
                    ret = game.set_answer(player, [])
                    assert ret, 'random answer is not valid'
                else:
                    answer = list(range(len(game.question.choices)))
                    random.shuffle(answer)
                    ret = game.set_answer(player, answer[:random.randrange(len(answer))])
                    assert ret, 'random answer is not valid'

            elif game.question.__class__.__name__ == "DeclareBlockers":
                answer = {}
                for i, ch in enumerate(game.question.choices):
                    if random.random() > 0.7:
                        answer[i] = random.randrange(len(ch['attackers']))
                ret = game.set_answer(player, answer)
                assert ret, 'random answer is not valid'

            elif game.question.__class__.__name__ == "OrderBlockers":
                answer = []
                for ch in game.question.choices:
                    ans = list(range(len(ch['blockers'])))
                    random.shuffle(ans)
                    answer.append(ans)
                ret = game.set_answer(player, answer)
                assert ret, 'random answer is not valid'

            else:
                assert False, game.question

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
