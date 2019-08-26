from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from app.config import Config

app = Flask(__name__, static_folder='../client', static_url_path='/client')

app.config.from_object(Config)
db = SQLAlchemy(app)
login_mgr = LoginManager(app)
Migrate(app, db)

from app import routes
from app import game_routes
from app import card_routes
