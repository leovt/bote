from abilities import firesource_ability
from cards import ArtCard, RuleCard
from state import setup_duel, run_game
import energy

TEST_DECK = (
    [ArtCard(RuleCard('Firesource',
                      {'source', 'basic'},
                      {'firesource'},
                      [firesource_ability]))
    ]*20 +
    [ArtCard(RuleCard("Goblin Raiders",
                      {'creature'},
                      {'goblin'},
                      strength = 1,
                      toughness = 1,
                      cost = energy.RED,
                      ))
    ]*40)

try:
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    run_game(game)
except:
    import pdb
    pdb.post_mortem()
