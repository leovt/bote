from flask import render_template, redirect, flash, url_for, request, abort, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app import app, db
from app.models import User, Deck, DeckCard
from app.forms import LoginForm, PasswordForm

import time
import cards

@app.route('/whoami')
def hello():
    return render_template('base.html', title='Home')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('lobby'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect('/')
    return render_template('login.html', title='Sign-In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('hello'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            logout_user()
            return redirect(url_for('lobby'))

        current_user.set_password(form.password.data)
        db.session.commit()
        return redirect(url_for('lobby'))
    return render_template('password.html', title='Change Password', form=form)


@app.route('/')
def lobby():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('lobby.html')

global_chat_messages = []
global_lobby_users_last_seen = {}

@app.route('/chat_msg', methods=['POST'])
@login_required
def send_msg():
    global_chat_messages.append((current_user.username, request.data.decode('utf8')))
    return ('', 204)

@app.route('/chat_msg', methods=['GET'])
@login_required
def chat():
    try:
        first = int(request.args.get('first', 0))
    except ValueError:
        abort(400)
    if first < 0:
        abort(400)

    global_lobby_users_last_seen[current_user.username] = time.time()
    return jsonify([{'index': index, 'user': user, 'message': message}
        for index, (user, message) in enumerate(global_chat_messages[first:], first)])


@app.route('/lobby_users')
@login_required
def lobby_users():
    now = time.time()
    return jsonify([{
        'user': user,
        'status': ('away' if last_seen < now - 30 else 'here')}
        for user, last_seen in global_lobby_users_last_seen.items()
    ])


@app.route('/decks')
@login_required
def decks():
    decks = Deck.query.filter_by(owner_id=current_user.id)
    return render_template('decks.html', decks=decks)


@app.route('/decks', methods=['POST'])
@login_required
def new_deck():
    deck = Deck(owner_id=current_user.id, name="Unnamed Deck")
    db.session.add(deck)
    db.session.commit()
    return redirect(url_for('deck', deck_id=deck.id))


@app.route('/deck/<deck_id>')
@login_required
def deck(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    if (deck.owner_id != current_user.id):
        abort(403);
    return render_template('deck.html', deck=deck, cards=cards.all())

@app.route('/deck/<deck_id>', methods=['POST'])
@login_required
def save_deck(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    if (deck.owner_id != current_user.id):
        abort(403);
    if request.json is None:
        abort(415)
    deck.name = request.json['name']
    art_ids = {c.art_id for c in deck.cards}
    print("art_ids", art_ids)
    print("json", request.json)
    for art_id, count in request.json['cards'].items():
        art_id = int(art_id)
        count = int(count)
        if art_id in art_ids:
            deck.cards.filter_by(art_id=art_id).one().count = count
            art_ids.remove(art_id)
        else:
            db.session.add(DeckCard(deck_id=deck.id, art_id=art_id, count=count))
    for art_id in art_ids:
        db.session.delete(deck.cards.filter_by(art_id=art_id).one())
    db.session.commit()
    return ('', 204)
