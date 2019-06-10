import flask

app = flask.Flask('__name__')

@app.route('/')
def hello():
    return 'Hello, World!'

games = {}

from cards import ArtCard, rule_cards
from state import setup_duel, run_game

TEST_DECK = (
    [ArtCard(rule_cards[101])] * 20 +
    [ArtCard(rule_cards[102])] * 40)

games['test'] = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)

@app.route('/<game_id>/state')
def game_state(game_id):
    game = games.get(game_id)
    if not game:
        flask.abort(404)

    return flask.jsonify(game.player_view())

@app.route('/<game_id>/log')
def game_log(game_id):
    game = games.get(game_id)
    if not game:
        flask.abort(404)

    return flask.jsonify(game.event_log)
