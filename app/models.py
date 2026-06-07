from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import url_for
from datetime import datetime, timedelta

from app import db, login_mgr

from state import Game
import tools
from aiplayers import random_answer
from test_decks import AI_TEST_PLAYERS

games = {}


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
    owner = db.relationship("User")
    name = db.Column(db.String)
    public = db.Column(db.Boolean, nullable=False, default=False)
    cards = db.relationship('DeckCard', backref='deck', lazy='dynamic')

class DeckCard(db.Model):
    deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), primary_key=True)
    art_id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer)

class Table(db.Model):
    __tablename__ = 'game_table'

    id = db.Column(db.String(32), primary_key=True, default=tools.random_id)
    status = db.Column(db.String(32), nullable=False, default='deck_selection')
    player1 = db.Column(db.String(80), nullable=False)
    player2 = db.Column(db.String(80), nullable=True)
    deck1 = db.Column(db.JSON, nullable=True)
    deck2 = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def user1(self):
        return self.player1

    @property
    def user2(self):
        return self.player2

    @property
    def game(self):
        return games.get(self.id)

    def url(self):
        return url_for('game', game_id=self.id)

    def join_url(self):
        return url_for('join_game', game_id=self.id)

    def players(self):
        return [player for player in (self.player1, self.player2) if player]

    def has_player(self, player_id):
        return player_id in (self.player1, self.player2)

    def deck_for(self, player_id):
        if player_id == self.player1:
            return self.deck1
        if player_id == self.player2:
            return self.deck2
        return None

    def waiting_for_player(self, player_id):
        return self.has_player(player_id) and self.deck_for(player_id) is None

    def claim_second_seat(self, player_id):
        if self.player2 is None and player_id != self.player1:
            self.player2 = player_id
            return True
        return self.player2 == player_id

    def choose_deck(self, player_id, deck):
        if self.status != 'deck_selection' or not self.has_player(player_id):
            return False

        snapshot = {str(c.art_id): c.count for c in deck.cards}
        if player_id == self.player1 and self.deck1 is None:
            self.deck1 = snapshot
        elif player_id == self.player2 and self.deck2 is None:
            self.deck2 = snapshot
        else:
            return False

        if self.player1 and self.player2 and self.deck1 is not None and self.deck2 is not None:
            self.start()
        return True

    def _deck_snapshot(self, deck):
        return {int(art_id): int(count) for art_id, count in deck.items()}

    def start(self):
        games[self.id] = Game.create_duel(
            self.player1,
            self._deck_snapshot(self.deck1),
            self.player2,
            self._deck_snapshot(self.deck2))
        self.status = 'running'

    def hydrate_game(self):
        return self.game

    def player_for_identity(self, player_id):
        game = self.game
        if game is None:
            return None
        for player in game.players.values():
            if player.name == player_id:
                return player
        return None

    def advance_game_state(self):
        if self.status != 'running':
            return

        game = self.game
        if game is None:
            return

        while True:
            question = game.next_decision()
            if not question:
                self.status = 'ended'
                return

            if question.player.name in AI_TEST_PLAYERS:
                answer = random_answer(question)
                ret = game.set_answer(question.player, answer)
                assert ret, 'random answer is not valid'
                game.question = None
                game.answer = answer
            else:
                return question

    def __str__(self):
        return f"BOTE Table {self.player1} vs. {self.player2 or 'waiting'}"


class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenger = db.Column(db.String(80), nullable=False)
    target = db.Column(db.String(80), nullable=False)
    table_id = db.Column(db.String(32), db.ForeignKey('game_table.id'), nullable=False)
    table = db.relationship('Table')
    status = db.Column(db.String(32), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @classmethod
    def expire_old(cls, max_age=timedelta(minutes=5)):
        cutoff = datetime.utcnow() - max_age
        for challenge in cls.query.filter_by(status='pending').filter(cls.created_at < cutoff):
            challenge.status = 'expired'
            challenge.table.status = 'ended'
