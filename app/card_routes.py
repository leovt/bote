from flask import abort, jsonify, request, render_template
from flask_login import login_required, current_user

from app import app
import cards

from app.models import Card, ArtCard


IMAGE_PREFIX = '/client/'


@app.route('/card/<card_id>')
def card_view(card_id):
    card = Card.query.filter_by(card_id=card_id).first_or_404()
    name = card.name(request.headers.get('accept-language',''))
    return render_template('card.html', card=card, name=name)


def get_lang(names, lang):
    ''' From a dict of {lang: name} return the best match
      - the requested language
      - English
      - any value in the dict
    '''
    if not names:
        return None
    name = names.get(lang)
    if name:
        return name
    name = names.get('en')
    if name:
        return name
    return next(names.values())


@app.route('/card/svg/<art_id>/<lang>')
def art_svg(art_id, lang):
    art_card = cards.art_card_spec(int(art_id))
    if not art_card:
        abort(404)
    card = cards.card_spec(art_card['card_id'])
    assert card, art_card['card_id']
    return render_template('card.svg',
        name = get_lang(card['names'], lang),
        cost = card.get('cost',''),
        type = card['type'],
        stats = f"{card['strength']} / {card['toughness']}" if 'strength' in card else '',
        attribution = art_card['attribution'],
        image_url = IMAGE_PREFIX + art_card['image'],
    )
