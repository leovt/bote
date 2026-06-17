from flask import abort, jsonify, redirect, request, render_template, url_for

from app import app, db
from app.anonymous import (
    current_display_name,
    display_name_for,
    ensure_player_id,
    is_guest_display_name,
    touch_presence,
)
from app.models import Challenge, Deck, Table
from app.game_view import game_result_for, serialize_game_view

from test_decks import AI_TEST_PLAYERS


def _table_or_404(game_id):
    return Table.query.get_or_404(game_id)


def _active_table_for(player_id):
    return Table.query.filter(
        Table.status != 'ended',
        db.or_(Table.player1 == player_id, Table.player2 == player_id)
    ).first()


def _public_decks():
    return Deck.query.filter_by(public=True).all()


def _viewer_for_table(table):
    player_id = ensure_player_id()
    if not table.has_player(player_id):
        return None
    return table.player_for_identity(player_id)


def _replace_player_names(value):
    if isinstance(value, list):
        return [_replace_player_names(item) for item in value]
    if isinstance(value, dict):
        replaced = {
            key: _replace_player_names(item)
            for key, item in value.items()
        }
        if 'player_id' in replaced and 'name' in replaced:
            replaced['name'] = display_name_for(replaced['name'])
        return replaced
    return value


@app.route('/games')
def my_games():
    player_id, _ = touch_presence()
    tables = Table.query.filter(
        db.or_(Table.player1 == player_id, Table.player2 == player_id)
    ).order_by(Table.updated_at.desc()).all()
    return jsonify([{
        'id': table.id,
        'url': table.url(),
        'join_url': table.join_url(),
        'players': [display_name_for(player) for player in table.players()],
        'status': table.status,
        }
        for table in tables
    ])


@app.route('/game/<game_id>')
def game(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if not table.has_player(player_id):
        abort(403)

    if table.status == 'deck_selection':
        display_name = current_display_name()
        return render_template(
            'choose_deck.html',
            game=table,
            player_id=player_id,
            display_name_for=display_name_for,
            show_name_prompt=is_guest_display_name(display_name),
            pub_decks=_public_decks())

    if table.status not in ('running', 'ended'):
        abort(409)

    my_name = display_name_for(player_id)
    opponent = table.player2 if table.player1 == player_id else table.player1
    op_name = display_name_for(opponent)
    viewer = _viewer_for_table(table)
    result = game_result_for(table, viewer)
    return render_template(
        'game.html',
        game=table,
        my_name=my_name,
        op_name=op_name,
        ended_message=result['message'] if result else 'Game has ended',
        rematch_url=url_for('rematch_game', game_id=table.id))


@app.route('/game/<game_id>/rematch')
def rematch_game(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if not table.has_player(player_id):
        abort(403)

    opponent = table.player2 if table.player1 == player_id else table.player1
    new_table = Table(player1=player_id, player2=opponent, status='deck_selection')
    ai_player = AI_TEST_PLAYERS.get(opponent)
    if ai_player is not None:
        new_table.deck2 = {str(art_id): count for art_id, count in ai_player['deck'].items()}
    db.session.add(new_table)
    db.session.commit()
    return redirect(new_table.url())


@app.route('/game/<game_id>/join')
def join_game(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if table.player1 == player_id:
        return redirect(table.url())
    if table.player2 and table.player2 != player_id:
        abort(409)
    if not table.claim_second_seat(player_id):
        abort(409)
    db.session.commit()
    return redirect(table.url())


@app.route('/game/<game_id>/choose_deck', methods=['POST'])
def choose_deck(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if request.json is None:
        abort(415)
    if not table.has_player(player_id):
        abort(403)

    try:
        deck_id = int(request.json['deck_id'])
    except (KeyError, TypeError, ValueError):
        abort(400)
    deck = db.session.get(Deck, deck_id)
    if not deck or not deck.public:
        abort(400)

    if not table.choose_deck(player_id, deck):
        abort(409)
    db.session.commit()
    return ('', 204)


@app.route('/game/create', methods=["POST"])
def create_game():
    if request.json is None:
        abort(415)

    player_id, _ = touch_presence()
    opponent = request.json.get('opponent')
    ai_player = AI_TEST_PLAYERS.get(opponent)
    if ai_player is None:
        abort(400)

    table = Table(player1=player_id, player2=opponent, status='deck_selection')
    table.deck2 = {str(art_id): count for art_id, count in ai_player['deck'].items()}
    db.session.add(table)
    db.session.commit()
    return "", 201, {'location': table.url()}


@app.route('/game/invite', methods=["POST"])
def create_invite():
    player_id, _ = touch_presence()
    table = Table(player1=player_id, status='deck_selection')
    db.session.add(table)
    db.session.commit()
    return jsonify({
        'id': table.id,
        'url': table.url(),
        'join_url': table.join_url(),
    }), 201, {'location': table.url()}


@app.route('/challenge', methods=['POST'])
def create_challenge():
    if request.json is None:
        abort(415)
    challenger, _ = touch_presence()
    target = request.json.get('target')
    if not target or target == challenger:
        abort(400)
    Challenge.expire_old()
    db.session.commit()
    if _active_table_for(target):
        return jsonify({'error': 'Player is already in another game.'}), 409

    table = Table(player1=challenger, player2=target, status='waiting')
    challenge = Challenge(challenger=challenger, target=target, table=table)
    db.session.add(table)
    db.session.add(challenge)
    db.session.commit()
    return jsonify({'challenge_id': challenge.id, 'table_url': table.url()}), 201


@app.route('/challenges')
def challenges():
    player_id, _ = touch_presence()
    Challenge.expire_old()
    db.session.commit()
    incoming = Challenge.query.filter_by(target=player_id, status='pending').all()
    outgoing = Challenge.query.filter_by(challenger=player_id).filter(
        Challenge.status.in_(('accepted', 'declined', 'expired'))
    ).all()
    return jsonify({
        'incoming': [{
            'id': challenge.id,
            'from': display_name_for(challenge.challenger),
            'table_url': challenge.table.url(),
        } for challenge in incoming],
        'outgoing': [{
            'id': challenge.id,
            'status': challenge.status,
            'target': display_name_for(challenge.target),
            'table_url': challenge.table.url(),
        } for challenge in outgoing],
    })


@app.route('/challenge/<int:challenge_id>/respond', methods=['POST'])
def respond_challenge(challenge_id):
    if request.json is None:
        abort(415)
    player_id, _ = touch_presence()
    challenge = Challenge.query.get_or_404(challenge_id)
    if challenge.target != player_id:
        abort(403)
    if challenge.status != 'pending':
        abort(409)

    response = request.json.get('response')
    if response == 'accept':
        challenge.status = 'accepted'
        challenge.table.status = 'deck_selection'
    elif response == 'decline':
        challenge.status = 'declined'
        challenge.table.status = 'ended'
    else:
        abort(400)
    db.session.commit()
    return jsonify({'table_url': challenge.table.url(), 'status': challenge.status})


@app.route('/api/game/<game_id>/status')
def game_status(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if not table.has_player(player_id):
        abort(403)
    return jsonify({
        'status': table.status,
        'game_url': table.url(),
        'player1': display_name_for(table.player1),
        'player2': display_name_for(table.player2),
        'player1_ready': table.deck1 is not None,
        'player2_ready': table.deck2 is not None,
    })


@app.route('/game/load', methods=["POST"])
def load_game():
    abort(404)


@app.route('/game/<game_id>/answer', methods=["POST"])
def answer(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if table.status != 'running' or not table.has_player(player_id):
        abort(403)

    game = table.game
    if game is None:
        abort(409)
    if game.answer is not None or game.question is None:
        abort(409)

    player = table.player_for_identity(player_id)
    if game.question.player is not player:
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
    db.session.commit()
    return ('', 204)


@app.route('/api/game/<game_id>/view')
def game_view(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if not table.has_player(player_id):
        abort(403)

    if table.status == 'running' and table.game is None:
        abort(409)

    question = table.advance_game_state()
    player = _viewer_for_table(table)
    if table.status == 'running' and player is None:
        abort(403)

    response = serialize_game_view(table, player, display_name_for)
    if question:
        response['question'] = question.serialize_for(player)
    response = _replace_player_names(response)
    db.session.commit()
    return jsonify(response)


@app.route('/game/<game_id>/save', methods=["POST"])
def savegame(game_id):
    abort(404)


@app.route('/game/<game_id>/log')
def game_log(game_id):
    table = _table_or_404(game_id)
    player_id, _ = touch_presence()
    if not table.has_player(player_id):
        abort(403)

    game = table.hydrate_game()
    if game is None:
        abort(409)

    player = table.player_for_identity(player_id)

    try:
        first = int(request.args.get('first', 0))
    except ValueError:
        abort(400)
    if first < 0:
        abort(400)

    filter = request.args.get('filter')
    if filter:
        filter = set(x.strip() for x in filter.split('_'))

    question = table.advance_game_state()

    event_log = []
    for event_no, event in enumerate(game.event_log[first:], first):
        serialized = event.serialize_for(player, game)
        serialized['event_no'] = event_no
        serialized = _replace_player_names(serialized)
        if filter is None or serialized['event_id'] in filter:
            event_log.append(serialized)

    response = {
        'status': table.status,
        'event_log': event_log,
    }
    if question:
        response['question'] = _replace_player_names(question.serialize_for(player))

    db.session.commit()
    return jsonify(response)
