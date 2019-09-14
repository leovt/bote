import sys
import traceback
import pdb
import random

from state import setup_duel, game_events
from dummy_deck import TEST_DECK


sys.setrecursionlimit(50)

def random_answer(question):
    if question.__class__.__name__ == "ChooseAction":
        return random.randrange(len(question.choices))

    if question.__class__.__name__ == "DeclareAttackers":
        if not question.choices:
            return []
        else:
            answer = list(range(len(question.choices)))
            random.shuffle(answer)
            return answer[:random.randrange(len(answer))]

    if question.__class__.__name__ == "DeclareBlockers":
        answer = {}
        for i, ch in enumerate(question.choices):
            if random.random() > 0.7:
                answer[i] = random.randrange(len(ch['attackers']))
        return answer

    elif question.__class__.__name__ == "OrderBlockers":
        answer = []
        for ch in question.choices:
            ans = list(range(len(ch['blockers'])))
            random.shuffle(ans)
            answer.append(ans)
        return answer

    assert False, question


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
