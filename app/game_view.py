from keywords import KEYWORDS


def _player_summary(game, player, viewer, name_for):
    return {
        'player_id': player.player_id,
        'name': name_for(player.name),
        'is_me': player is viewer,
        'life': player.life,
        'energy': {
            'pool': str(player.energy_pool.energy),
            'capacity': player.energy_pool.energy.total,
            'total': player.energy_pool.energy.total,
            'breakdown': {
                'red': player.energy_pool.energy.red,
                'yellow': player.energy_pool.energy.yellow,
                'blue': player.energy_pool.energy.blue,
                'green': player.energy_pool.energy.green,
                'white': player.energy_pool.energy.white,
                'colorless': max(0, player.energy_pool.energy.total
                    - player.energy_pool.energy.red
                    - player.energy_pool.energy.yellow
                    - player.energy_pool.energy.blue
                    - player.energy_pool.energy.green
                    - player.energy_pool.energy.white),
            },
        },
        'hand_count': len(player.hand),
        'library_count': len(player.library),
        'graveyard_count': len(player.graveyard),
        'has_priority': player is game.priority_player,
    }


def _visible_card(card, viewer):
    data = card.serialize_for(viewer)
    data['types'] = sorted(card.types)
    data['subtypes'] = sorted(card.subtypes)
    data['cost'] = str(card.cost)
    data['strength'] = card.strength
    data['toughness'] = card.toughness
    data['abilities'] = [
        ability for ability in card.abilities
        if isinstance(ability, dict)
    ]
    return data


def _hidden_card(card_id):
    return {
        'card_id': card_id,
        'hidden': True,
        'url': '/client/backface.png',
    }


def _card_ref(card, viewer, visible):
    if visible:
        return _visible_card(card, viewer)
    return _hidden_card(card.known_identity)


def _permanent_view(permanent, viewer):
    keywords = [
        keyword for keyword in KEYWORDS
        if permanent.has(keyword)
    ]
    return {
        'perm_id': permanent.perm_id,
        'card': _visible_card(permanent.card, viewer),
        'controller_id': permanent.controller.player_id,
        'controller': permanent.controller.serialize_for(viewer),
        'types': sorted(permanent.types),
        'subtypes': sorted(permanent.subtypes),
        'strength': permanent.strength,
        'toughness': permanent.toughness,
        'damage': permanent.total_damage_received,
        'keywords': keywords,
        'status': {
            'tapped': permanent.tapped,
            'attacking_player_id': (
                permanent.attacking.player_id
                if permanent.attacking else None
            ),
            'blocking_perm_id': (
                permanent.blocking.perm_id
                if permanent.blocking else None
            ),
            'blocker_perm_ids': [
                blocker.perm_id for blocker in permanent.blockers
            ],
        },
        'choices': {
            key: _choice_ref(value)
            for key, value in permanent.choices.items()
        },
    }


def _choice_ref(value):
    if hasattr(value, 'perm_id'):
        return {'type': 'permanent', 'perm_id': value.perm_id}
    if hasattr(value, 'player_id'):
        return {'type': 'player', 'player_id': value.player_id}
    return value


def _stack_item_view(item, viewer):
    data = item.serialize_for(viewer)
    if 'controller' in data and hasattr(item.controller, 'player_id'):
        data['controller_id'] = item.controller.player_id
    if 'card' in data:
        card = getattr(item, 'card', None)
        if card is None and hasattr(item, 'permanent'):
            card = item.permanent.card
        if card is not None:
            data['card'] = _visible_card(card, viewer)
    return data


def _public_zone_card(card, viewer):
    return _visible_card(card, viewer)


def _player_zones(player, viewer):
    hand_visible = player is viewer
    return {
        'player_id': player.player_id,
        'hand': [
            _card_ref(card, viewer, hand_visible)
            for card in player.hand
        ] if hand_visible else [],
        'hand_count': len(player.hand),
        'library_count': len(player.library),
        'graveyard': [
            _public_zone_card(card, viewer)
            for card in player.graveyard
        ],
    }


def serialize_game_view(frontend_game, viewer, name_for=lambda name: name):
    game = frontend_game.game
    if game is None:
        return {
            'game_id': frontend_game.id,
            'status': frontend_game.status,
            'players': [],
            'zones': {},
            'battlefield': [],
            'stack': [],
            'question': None,
        }

    question = game.question.serialize_for(viewer) if game.question else None
    return {
        'game_id': frontend_game.id,
        'status': frontend_game.status,
        'viewer_player_id': viewer.player_id if viewer else None,
        'turn': {
            'step': game.step.name,
            'active_player_id': (
                game.active_player.player_id
                if game.active_player else None
            ),
            'priority_player_id': (
                game.priority_player.player_id
                if game.priority_player else None
            ),
        },
        'players': [
            _player_summary(game, player, viewer, name_for)
            for player in game.players.values()
        ],
        'zones': {
            player.player_id: _player_zones(player, viewer)
            for player in game.players.values()
        },
        'battlefield': [
            _permanent_view(permanent, viewer)
            for permanent in game.battlefield
        ],
        'stack': [
            _stack_item_view(item, viewer)
            for item in game.stack
        ],
        'question': question,
        'event_count': len(game.event_log),
    }
