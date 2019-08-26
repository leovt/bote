import traceback
import pdb

import cli
from state import setup_duel, game_events
from dummy_deck import TEST_DECK


def print_player_view(view):
    print('=' * 80)
    print(f'It is the {view.step} of {view.players[view.active_player].name}s turn.')
    print('Players:')
    for p in view.players.values():
        print(f'    {p.name}: {p.life} life; {p.hand_size} cards in hand, {p.energy_pool} in pool')
        if p.graveyard:
            print('        Graveyard:')
            for card in p.graveyard:
                print(f'            {card.name}')
    print('-' * 80)
    if view.stack:
        print('Stack')
        for item in reversed(view.stack):
            print(f'    {item}')
        print('-' * 80)
    print('Battlefield')
    for pid, p in view.players.items():
        print('    Controlled by', p.name)
        nothing = True
        for obj in view.battlefield.values():
            if obj.controller == pid:
                print('       ', obj.name)
                nothing = False
        if nothing:
            print('        nothing')
    print('-' * 80)
    print('Your hand:')
    for card in view.you.hand:
        print('   ', card.name)

def run_game(game):
    event_stream = game_events(game)
    for event in event_stream:
        game.handle(event)
        if game.question:
            print_player_view(game.player_view(game.question.player))
            game.answer = cli.ask_question(game.question)
            game.question = None

try:
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    run_game(game)
except:
    traceback.print_exc()
    pdb.post_mortem()
