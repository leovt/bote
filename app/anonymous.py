import time
import uuid
import re

from flask import session

from test_decks import AI_TEST_PLAYERS


PLAYER_SESSION_KEY = 'anonymous_player_id'
NAME_SESSION_KEY = 'anonymous_display_name'

_display_names = {}
_last_seen = {}
GUEST_NAME_RE = re.compile(r'^Guest\s+\w+$')
LOBBY_HERE_SECONDS = 30
LOBBY_HIDE_AFTER_SECONDS = 60 * 60
ANONYMOUS_CLEANUP_SECONDS = 24 * 60 * 60


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


def is_guest_display_name(name):
    return bool(GUEST_NAME_RE.fullmatch((name or '').strip()))


def touch_presence():
    player_id = ensure_player_id()
    name = current_display_name()
    _last_seen[player_id] = time.time()
    return player_id, name


def display_name_for(player_id):
    if player_id in AI_TEST_PLAYERS:
        return AI_TEST_PLAYERS[player_id]['name']
    if not player_id:
        return 'Waiting...'
    if not player_id.startswith('session:'):
        return player_id
    return _display_names.get(player_id) or default_display_name(player_id)


def active_players(here_age=LOBBY_HERE_SECONDS, hide_after=LOBBY_HIDE_AFTER_SECONDS):
    now = time.time()
    return [
        {
            'player_id': player_id,
            'name': display_name_for(player_id),
            'status': 'away' if last_seen < now - here_age else 'here',
        }
        for player_id, last_seen in sorted(
            _last_seen.items(),
            key=lambda item: display_name_for(item[0]).lower())
        if now - last_seen < hide_after
        and not is_guest_display_name(display_name_for(player_id))
    ]


def pop_stale_anonymous_players(max_age=ANONYMOUS_CLEANUP_SECONDS):
    cutoff = time.time() - max_age
    stale_player_ids = [
        player_id
        for player_id, last_seen in _last_seen.items()
        if player_id.startswith('session:') and last_seen < cutoff
    ]
    for player_id in stale_player_ids:
        _last_seen.pop(player_id, None)
        _display_names.pop(player_id, None)
    return stale_player_ids
