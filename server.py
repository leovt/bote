import flask

app = flask.Flask('__name__',
                  static_folder='client')

@app.route('/')
def hello():
    return 'Hello, World!'

games = {}

from cards import ArtCard, rule_cards
from state import setup_duel, game_events

TEST_DECK = (
    [ArtCard(rule_cards[101])] * 20 +
    [ArtCard(rule_cards[102])] * 40)

games['test'] = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
games['test'].events = game_events(games['test'])

def advance_game_state(game):
    while not game.question:
        event = next(game.events)
        game.handle(event)
advance_game_state(games['test'])

@app.route('/<game_id>/answer', methods=["POST"])
def answer(game_id):
    game = games.get(game_id)
    if not game:
        flask.abort(404)
    if game.answer is not None or game.question is None:
        flask.abort(409)

    # TODO: check the correct player is answering etc
    print('posting an answer')
    print(flask.request.data)
    if flask.request.json is None:
        flask.abort(415)

    try:
        answer = flask.request.json['answer']
    except:
        flask.abort(400)

    number_of_choices = len(game.question[2])

    if game.question[3]:
        # multiple choice
        if  not (isinstance(answer, list) and
            all(isinstance(x, int) for x in answer) and
            all(0 <= x < number_of_choices)):
            return('invalid answer', 400)
    else:
        if not (isinstance(answer, int) and 0 <= answer < number_of_choices):
            return ('invalid answer', 400)

    game.question = None
    game.answer = answer
    advance_game_state(game)
    return ('', 204)

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
