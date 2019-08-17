from flask import abort, jsonify, request
from flask_login import login_required, current_user

from app import app

games = {}

from cards import ArtCard, rule_cards
from state import setup_duel, game_events
import tools

TEST_DECK = (
    [ArtCard(rule_cards[101])] * 20 +
    [ArtCard(rule_cards[102])] * 40)

def advance_game_state(game):
    while not game.question:
        event = next(game.events)
        game.handle(event)


@app.route('/create', methods=["POST"])
@login_required
def create_game():
    game = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
    game.events = game_events(game)
    game_id = tools.random_id()
    advance_game_state(game)
    games[game_id] = game
    return "", 201, {'location': '/'+game_id}


@app.route('/<game_id>/answer', methods=["POST"])
@login_required
def answer(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)
    if game.answer is not None or game.question is None:
        abort(409)

    for p in game.players:
        if p.name == current_user.username:
            player = p
            break
    else:
        abort(403)

    print('posting an answer')
    print(request.data)
    if request.json is None:
        abort(415)

    try:
        ans = flask.request.json['answer']
    except:
        abort(400)

    if not game.set_answer(player, answer):
        return('invalid answer', 400)

    game.question = None
    game.answer = ans
    advance_game_state(game)
    return ('', 204)

@app.route('/<game_id>/state')
def game_state(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)

    return jsonify(game.player_view())

@app.route('/<game_id>/log')
def game_log(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)

    if current_user.is_anonymous:
        player = None
    else:
        for p in game.players:
            if p.name == current_user.username:
                player = p
                break
        else:
            player = None

    try:
        first = int(request.args.get('first', 0))
    except ValueError:
        abort(400)
    if first<0:
        abort(400)

    return jsonify(dict(enumerate((e.serialize_for(player) for e in game.event_log[first:]), first)))
