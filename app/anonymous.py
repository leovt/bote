import time
import uuid

from flask import session


PLAYER_SESSION_KEY = 'anonymous_player_id'
NAME_SESSION_KEY = 'anonymous_display_name'

_display_names = {}
_last_seen = {}


def _short_id(player_id):
    return player_id.split(':', 1)[1][:4]


def ensure_player_id():
    player_id = session.get(PLAYER_SESSION_KEY)
    if not player_id:
        player_id = f'session:{uuid.uuid4().hex}'
        session[PLAYER_SESSION_KEY] = player_id
    return player_id


def default_display_name(player_id=None):
    player_id = player_id or ensure_player_id()
    return f'Guest {_short_id(player_id)}'


def current_display_name():
    player_id = ensure_player_id()
    name = session.get(NAME_SESSION_KEY) or default_display_name(player_id)
    _display_names[player_id] = name
    return name


def set_current_display_name(name):
    player_id = ensure_player_id()
    name = (name or '').strip()
    if not name:
        name = default_display_name(player_id)
    name = name[:32]
    session[NAME_SESSION_KEY] = name
    _display_names[player_id] = name
    return name


def touch_presence():
    player_id = ensure_player_id()
    name = current_display_name()
    _last_seen[player_id] = time.time()
    return player_id, name


def display_name_for(player_id):
    if player_id == '__ai__random__':
        return 'Random AI'
    if not player_id:
        return 'Waiting...'
    if not player_id.startswith('session:'):
        return player_id
    return _display_names.get(player_id) or default_display_name(player_id)


def active_players(max_age=30):
    now = time.time()
    return [
        {
            'player_id': player_id,
            'name': display_name_for(player_id),
            'status': 'away' if last_seen < now - max_age else 'here',
        }
        for player_id, last_seen in sorted(
            _last_seen.items(),
            key=lambda item: display_name_for(item[0]).lower())
        if now - last_seen < max_age * 4
    ]
