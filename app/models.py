from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import url_for

from app import db, login_mgr

from dummy_deck import TEST_DECK
from state import setup_duel
import tools
from aiplayers import random_answer

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_mgr.user_loader
def load_user(uid):
    return User.query.get(int(uid))

class Deck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String)
    cards = db.relationship('DeckCard', backref='deck', lazy='dynamic')

class DeckCard(db.Model):
    deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), primary_key=True)
    art_id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer)

class GameFrontend:
    def __init__(self, user1, user2):
        self.status = 'choose_deck'
        self.user1 = user1
        self.user2 = user2
        self.deck1 = None
        self.deck2 = None
        self.game = None
        self.id = tools.random_id()
        if user2 == '__ai__random__':
            self.deck2 = TEST_DECK


    def choose_deck(self, user, deck):
        if self.status != 'choose_deck':
            return

        if user == self.user1 and self.deck1 is None:
            self.deck1 = deck
        if user == self.user2 and self.deck2 is None:
            self.deck2 = deck

        if self.deck1 is not None and self.deck2 is not None:
            self.game = setup_duel(self.user1, TEST_DECK, self.user2, TEST_DECK)
            self.game.run()
            self.status = 'started'


    def advance_game_state(self):
        if self.status != 'started':
            return

        while True:
            question = self.game.next_decision()
            if not question:
                self.status = 'ended'
                return

            if question.player.name == '__ai__random__':
                answer = random_answer(question)
                ret = self.game.set_answer(question.player, answer)
                assert ret, 'random answer is not valid'
                self.game.question = None
            else:
                return question


    def url(self):
        return url_for('game', game_id=self.id)
