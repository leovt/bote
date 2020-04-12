from flask import abort, jsonify, request, render_template
from flask_login import login_required, current_user

from app import app
from app.models import Deck, GameFrontend


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
    return render_template('game.html')


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


@app.route('/game/<game_id>/log')
def game_log(game_id):
    game = games.get(game_id)
    if not game:
        abort(404)

    if current_user.is_anonymous:
        player = None
    else:
        for p in game.game.players:
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

    question = game.advance_game_state()
    response = {
        'status': game.status,
        'event_log': dict(enumerate((e.serialize_for(player, game.game) for e in game.game.event_log[first:]), first)),
    }
    if question:
        response['question'] = question.serialize_for(player)

    return jsonify(response)
