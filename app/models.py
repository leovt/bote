from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app import db, login_mgr

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


class Language(db.Model):
    lang_id = db.Column(db.String(2), primary_key=True)
    name = db.Column(db.String)


class Type(db.Model):
    type_id = db.Column(db.Integer, primary_key=True)


class TypeTranslation(db.Model):
    lang_id = db.Column(db.String(2), db.ForeignKey('language.lang_id'), primary_key=True)
    type_id = db.Column(db.Integer, db.ForeignKey('type.type_id'), primary_key=True)
    type_name = db.Column(db.String(50))


class RuleCardName(db.Model):
    lang_id = db.Column(db.String(2), db.ForeignKey('language.lang_id'), primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.card_id'), primary_key=True)
    card_name = db.Column(db.String(50))


card_type = db.Table('card_type',
    db.Column('type_id', db.String(2), db.ForeignKey('type.type_id'), primary_key=True),
    db.Column('card_id', db.Integer, db.ForeignKey('card.card_id'), primary_key=True)
)


class Card(db.Model):
    card_id = db.Column(db.Integer, primary_key=True)
    is_token = db.Column(db.Boolean)
    types = db.relationship("Type", secondary=card_type)
    strength = db.Column(db.Integer)
    toughness = db.Column(db.Integer)


class ArtCard(db.Model):
    art_id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.card_id'))
    #...Image
    #...Flavour Text
