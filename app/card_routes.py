import base64
import mimetypes
from flask import abort, jsonify, request, render_template, redirect, url_for

from app import app
import cards
from abilities import describe_effect


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


def create_data_url(filename):
    MISSING_IMAGE = (
    'iVBORw0KGgoAAAANSUhEUgAAAPAAAACgAgMAAABPtQn2AAAACVBMVEX///8AAADtHCQFH1MiAA'
    'ACtElEQVRo3u2aQW7bMBQFBS99lNyn98lRvBRyyjYm4ikwi/GngRYBopUUa8jPN6YcUTp+vbD9'
    'wN8J/vj4OMbbH+gLfp+yl7/gcwq/fcFX6p5UfbvDl8+9GXv9HOodPt6mdS/iDq92pnHdFrxGMK'
    '36WPDKbhjX+YAvk7ofpy94NTWTfABLdUoGXvGNJAMvcSPJwLT2rGRgxvG0ZGASfFYyMO4mcQFL'
    'dUkGpsVBXMBSnVUDO7KOC7gj00nAHZnLA8Z+zwnBHZmVAOfs4AzBtNuSDdfsIBXDrRofhrGYkg'
    '3TdEo23KqJxHCrRoZhRLZkYLUekgWXavIwnKoxYThV84HhUE1JAVs1YSRs1WgIGJ31V+BUTT2G'
    'UzVJGC7VOAgYo2EfWN1EMcAxQGIImGhDAHBI5bhhenIlDTNGMijY6ZJ+wvbKQcJWTRkBW7Xjah'
    'iC6BO2akaQsFVTQ8NW7bgaBqKRgq2a8hO2aoJr2KqJK2Gr1pxoGNVITth1E9cQPhZ8TGFUE9cQ'
    'vlD1DEb1/+j5ypj/bdqXPc+Y2v6GbX63uRDtzqq3vfnMjNy9klxfuYatnMdXT65/7BRsyRu/GE'
    'hm8Alb8u6vJHrZb1i9SXXCjFOqGyZhqU4Ytxw27K4opGEG6QgaJl6Hv///9pkw/UQt03uMW8BU'
    'HQ3O76veAyacKGd+LxkwZ4WC+f3zWTDJRI7jNYNbwJwSqmOdJFTHCk2oHq8NCQ7Janl7PewUHJ'
    'KV5vYa4E1wSFbjse4ZqmPFNVTvrvUK1iehent9+xRsyaF6d03/JliSW/XrzzFSslUDh+R4diPJ'
    'XTewJXdkwJbcswPYkjsy4OnTQWBL7siAJblnB7Alt+oHbMk9Ox4wkgeq48l3qF4wkkeqX3nav+'
    'BZXKh+5Q2Hc+PdCup+/a0O4prV/Z1fg/mBJ9tvPSCnP7LvLHgAAAAASUVORK5CYII=')
    try:
        with open(filename, 'rb') as infile:
            data = base64.b64encode(infile.read()).decode('ascii')
        mimetype, _ = mimetypes.guess_type(filename)
    except OSError:
        data = MISSING_IMAGE
        mimetype = 'image/png'
    return f'data:{mimetype};base64,{data}'


def str_ability(a, lang):
    if 'cost' in a:
        return f"{a['cost']}: {describe_effect(a['effect'], lang)}"
    if 'keyword' in a:
        return a['keyword'] #TODO: translate
    if 'trigger' in a:
        return str(a)



@app.route('/card/svg/<art_id>/<lang>')
def art_svg(art_id, lang):
    art_card = cards.art_card_spec(int(art_id))
    if not art_card:
        abort(404)
    card = cards.card_spec(art_card['card_id'])
    return render_template('card.svg',
        name = get_lang(card['names'], lang),
        cost = card.get('cost',''),
        type = card['type'],
        stats = f"{card['strength']} / {card['toughness']}" if 'strength' in card else '',
        attribution = art_card['attribution'],
        image_url = url_for('static', filename=art_card['image']),
        attributes = [str_ability(a, lang) for a in card.get('abilities', [])],
        frame = art_card['frame'],
    ), 200, {'Content-Type': 'image/svg+xml'}
