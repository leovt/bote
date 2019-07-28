import traceback
import pdb
import cli
from question import Question

from cards import ArtCard, rule_cards
from state import setup_duel, game_events

TEST_DECK = (
    [ArtCard(rule_cards[101])] * 20 +
    [ArtCard(rule_cards[102])] * 40)

def run_game(game):
    event_stream = game_events(game)
    for event in event_stream:
        game.handle(event)
        if isinstance(game.question, Question):
            game.answer = cli.ask_question(game.question)
            game.question = None
        elif game.question:
            game.answer = cli.ask_choice(*game.question)
            game.question = None

try:
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    run_game(game)
except:
    traceback.print_exc()
    pdb.post_mortem()
