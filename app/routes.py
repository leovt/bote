from flask import render_template, redirect, url_for, request, abort, jsonify

from app import app
from app.anonymous import (
    active_players,
    current_display_name,
    ensure_player_id,
    set_current_display_name,
    touch_presence,
)
from test_decks import AI_TEST_PLAYERS

@app.route('/whoami')
def hello():
    return render_template('base.html', title='Home')


@app.route('/login', methods=['POST', 'GET'])
def login():
    abort(404)


@app.route('/logout')
def logout():
    return redirect(url_for('hello'))


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    abort(404)


@app.route('/')
def lobby():
    touch_presence()
    return render_template(
        'lobby.html',
        ai_players=[
            {'player_id': player_id, 'name': player['name']}
            for player_id, player in AI_TEST_PLAYERS.items()
        ],
        savegames=[],
        player_id=ensure_player_id(),
        display_name=current_display_name())

global_chat_messages = []
@app.route('/chat_msg', methods=['POST'])
def send_msg():
    player_id, name = touch_presence()
    global_chat_messages.append((player_id, name, request.data.decode('utf8')))
    return ('', 204)

@app.route('/chat_msg', methods=['GET'])
def chat():
    try:
        first = int(request.args.get('first', 0))
    except ValueError:
        abort(400)
    if first < 0:
        abort(400)

    touch_presence()
    return jsonify([{'index': index, 'user': name, 'message': message}
        for index, (_, name, message) in enumerate(global_chat_messages[first:], first)])


@app.route('/lobby_users')
def lobby_users():
    player_id, _ = touch_presence()
    return jsonify([{
        'player_id': user['player_id'],
        'user': user['name'],
        'status': user['status'],
        'is_me': (user['player_id'] == player_id),
        }
        for user in active_players()
    ])


@app.route('/session/name', methods=['POST'])
def session_name():
    if request.json is None:
        abort(415)
    name = set_current_display_name(request.json.get('name'))
    touch_presence()
    return jsonify({'player_id': ensure_player_id(), 'display_name': name})


@app.route('/decks')
def decks():
    abort(404)


@app.route('/decks', methods=['POST'])
def new_deck():
    abort(404)


@app.route('/deck/<deck_id>')
def deck(deck_id):
    abort(404)

@app.route('/deck/<deck_id>', methods=['POST'])
def save_deck(deck_id):
    abort(404)
