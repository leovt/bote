import traceback
import pdb

from cards import ArtCard, rule_cards
from state import setup_duel, run_game

TEST_DECK = (
    [ArtCard(rule_cards[101])] * 20 +
    [ArtCard(rule_cards[102])] * 40)

try:
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    run_game(game)
except:
    traceback.print_exc()
    pdb.post_mortem()
