from flask import abort, jsonify, request, render_template
from flask_login import login_required, current_user

from app import app
from state import setup_duel, game_events
import tools
from dummy_deck import TEST_DECK
from aiplayers import random_answer


games = {}

@app.route('/games')
@login_required
def my_games():
    '''produce a list of games for the current user'''
    return jsonify([{
        'id': game_id,
        'url': '/game/'+game_id,
        'players': [p.name for p in game.players],}
        for game_id, game in games.items()
        if any(p.name == current_user.username for p in game.players)])


@app.route('/game/<game_id>')
@login_required
def game(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)
    return render_template('game.html')


def advance_game_state(game):
    while True:
        if game.question:
            if game.question.player.name == '__ai__random__':
                player = game.question.player
                answer = random_answer(game.question)
                ret = game.set_answer(player, answer)
                assert ret, f'random answer is not valid: {game.question}? {answer}.'
                game.question = None
                # todo: game.question = None is necessary, but this should not be necessary
                # and somehow be handled in set_answer
            else:
                break
        event = next(game.events)
        game.handle(event)


@app.route('/game/create', methods=["POST"])
@login_required
def create_game():
    game = setup_duel('Leo', TEST_DECK, '__ai__random__', TEST_DECK)
    game.events = game_events(game)
    game_id = tools.random_id()
    advance_game_state(game)
    games[game_id] = game
    return "", 201, {'location': '/game/'+game_id}


@app.route('/game/<game_id>/answer', methods=["POST"])
@login_required
def answer(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)
    if game.answer is not None or game.question is None:
        abort(409)

    if game.question.player.name == current_user.username:
        player = game.question.player
    else:
        abort(403)

    if request.json is None:
        abort(415)

    try:
        ans = request.json['answer']
    except KeyError:
        abort(400)

    if not game.set_answer(player, ans):
        return('invalid answer', 400)

    game.question = None
    game.answer = ans
    advance_game_state(game)
    return ('', 204)

@app.route('/game/<game_id>/state')
def game_state(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)

    return jsonify(game.player_view())

@app.route('/game/<game_id>/log')
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



# create a dummy game
# TODO: remove when frontend can create games
def create_game2():
    game = setup_duel('Leo', TEST_DECK, '__ai__random__', TEST_DECK)
    game.events = game_events(game)
    game_id = tools.random_id()
    advance_game_state(game)
    games[game_id] = game
    return "", 201, {'location': '/game/'+game_id}
create_game2()
