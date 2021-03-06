import os
import time
import yaml

from flask import abort, jsonify, request, render_template
from flask_login import login_required, current_user

from app import app
from app.models import Deck, GameFrontend

from state import Game


games = {}

@app.route('/games')
@login_required
def my_games():
    '''produce a list of games for the current user'''
    return jsonify([{
        'id': game_id,
        'url': game.url(),
        'players': [game.user1, game.user2],
        'status': game.status,
        }
        for game_id, game in games.items()
        if current_user.username in (game.user1, game.user2)
    ])


@app.route('/game/<game_id>')
@login_required
def game(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)
    if game.status == 'choose_deck':
        if (game.user1 == current_user.username and not game.deck1) or \
            (game.user2 == current_user.username and not game.deck2):
            my_decks = Deck.query.filter_by(owner_id=current_user.id)
            pub_decks = Deck.query.filter(Deck.owner_id != current_user.id, Deck.public == True)
        else:
            my_decks = pub_decks = []
        return render_template('choose_deck.html', game=game, my_decks=my_decks, pub_decks=pub_decks)

    if game.user1 == current_user.username:
        my_name = game.user1
        op_name = game.user2
    else:
        my_name = game.user2
        op_name = game.user1
    return render_template('game.html', game=game, my_name=my_name, op_name=op_name)


@app.route('/game/<game_id>/choose_deck', methods=['POST'])
@login_required
def choose_deck(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)
    deck = Deck.query.get(request.json['deck_id'])
    if not deck:
        abort(400)

    if deck.public or deck.owner_id == current_user.id:
        game.choose_deck(current_user.username, deck)
        return ('', 204)

    abort(400)


@app.route('/game/create', methods=["POST"])
@login_required
def create_game():
    if request.json is None:
        abort(415)

    new_game = GameFrontend(current_user.username, request.json['opponent'])
    games[new_game.id] = new_game
    assert new_game.url()
    return "", 201, {'location': new_game.url()}


@app.route('/game/load', methods=["POST"])
@login_required
def load_game():
    if current_user.username != "Leo":
        abort(404)

    if request.json is None:
        abort(415)

    fname = os.path.basename(request.json['filename'])

    with open('savegames/'+fname, encoding='utf8') as stream:
        data = yaml.safe_load(stream)

    new_game = GameFrontend(data['players'][0]['name'], data['players'][1]['name'])
    new_game.game = Game.deserialize(data)
    new_game.status = 'started'
    games[new_game.id] = new_game
    assert new_game.url()
    return "", 201, {'location': new_game.url()}


@app.route('/game/<game_id>/answer', methods=["POST"])
@login_required
def answer(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)

    game = game.game
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
    return ('', 204)


@app.route('/game/<game_id>/save', methods=["POST"])
@login_required
def savegame(game_id):
    if current_user.username != "Leo":
        abort(404)

    game = games.get(game_id)
    if not game:
        abort(404)

    now = time.strftime("%Y-%m-%d-%H-%M-%S")
    with open(f'savegames/game_{now}.yaml', 'w') as out:
        yaml.dump(game.game.serialize(), out)

    return ('', 204)


@app.route('/game/<game_id>/log')
def game_log(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)

    if current_user.is_anonymous:
        player = None
    else:
        for p in game.game.players.values():
            if p.name == current_user.username:
                player = p
                break
        else:
            player = None

    try:
        first = int(request.args.get('first', 0))
    except ValueError:
        abort(400)
    if first < 0:
        abort(400)

    filter = request.args.get('filter')
    if filter:
        filter = set(x.strip() for x in filter.split('_'))

    # call advance_game_state before preparing the event_log,
    # otherwise events created by advance_game_state would be missed
    question = game.advance_game_state()

    event_log = []
    for event_no, event in enumerate(game.game.event_log[first:], first):
        serialized = event.serialize_for(player, game.game)
        serialized['event_no'] = event_no
        if filter is None or serialized['event_id'] in filter:
            event_log.append(serialized)

    response = {
        'status': game.status,
        'event_log': event_log,
    }
    if question:
        response['question'] = question.serialize_for(player)

    return jsonify(response)
