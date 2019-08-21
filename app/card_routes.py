from flask import abort, jsonify, request, render_template
from flask_login import login_required, current_user

from app import app

from app.models import Card, ArtCard

@app.route('/card/<card_id>')
def card_view(card_id):
    card = Card.query.filter_by(card_id=card_id).first_or_404()
    name = card.name(request.headers.get('accept-language',''))
    return render_template('card.html', card=card, name=name)
