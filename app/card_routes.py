from flask import abort, jsonify, request, render_template, redirect, url_for

from app import app
import cards
from abilities import describe_effect


IMAGE_PREFIX = '/client/'


@app.route('/card/<card_id>')
def card_view(card_id):
    card = cards.card_spec(int(card_id))
    if not card:
        abort(404)
    name = get_lang(card['names'], request.headers.get('accept-language', '')[:2])
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
    

@app.route('/card/svg/<art_id>')
def art_svg_redirect(art_id):
    art_card = cards.art_card_spec(int(art_id))
    if not art_card:
        abort(404)
    card = cards.card_spec(art_card['card_id'])
    languages = {k:k for k in card['names']}
    lang = get_lang(languages, request.headers.get('accept-language', '')[:2])
    return redirect(url_for('art_svg', art_id=art_id, lang=lang))


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
        attributes = [f"{a['cost']}: {describe_effect(a['effect'], lang)}" for a in card.get('abilities', [])],
    ), 200, {'Content-Type': 'image/svg+xml'}
