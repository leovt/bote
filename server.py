import flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from forms import LoginForm
from config import Config
from flask_login import UserMixin, LoginManager, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

app = flask.Flask('__name__',
                  static_folder='client')
app.config.from_object(Config)
db = SQLAlchemy(app)
login_mgr = LoginManager(app)
Migrate(app, db)

@app.route('/')
def hello():
    return flask.render_template('base.html', title='Home')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return flask.redirect(flask.url_for('hello'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flask.flash('Invalid username or password')
            return flask.redirect(flask.url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return flask.redirect('/')
    return flask.render_template('login.html', title='Sign-In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return flask.redirect(flask.url_for('hello'))

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


games = {}

from cards import ArtCard, rule_cards
from state import setup_duel, game_events

TEST_DECK = (
    [ArtCard(rule_cards[101])] * 20 +
    [ArtCard(rule_cards[102])] * 40)

games['test'] = setup_duel('Leo', TEST_DECK, 'Marc', TEST_DECK)
games['test'].events = game_events(games['test'])

def advance_game_state(game):
    while not game.question:
        event = next(game.events)
        game.handle(event)
advance_game_state(games['test'])

@app.route('/<game_id>/answer', methods=["POST"])
def answer(game_id):
    game = games.get(game_id)
    if not game:
        flask.abort(404)
    if game.answer is not None or game.question is None:
        flask.abort(409)

    # TODO: check the correct player is answering etc
    print('posting an answer')
    print(flask.request.data)
    if flask.request.json is None:
        flask.abort(415)

    try:
        answer = flask.request.json['answer']
    except:
        flask.abort(400)

    number_of_choices = len(game.question[2])

    if game.question[3]:
        # multiple choice
        if  not (isinstance(answer, list) and
            all(isinstance(x, int) for x in answer) and
            all(0 <= x < number_of_choices)):
            return('invalid answer', 400)
    else:
        if not (isinstance(answer, int) and 0 <= answer < number_of_choices):
            return ('invalid answer', 400)

    game.question = None
    game.answer = answer
    advance_game_state(game)
    return ('', 204)

@app.route('/<game_id>/state')
def game_state(game_id):
    game = games.get(game_id)
    if not game:
        flask.abort(404)

    return flask.jsonify(game.player_view())

@app.route('/<game_id>/log')
def game_log(game_id):
    game = games.get(game_id)
    if not game:
        flask.abort(404)

    return flask.jsonify(game.event_log)
