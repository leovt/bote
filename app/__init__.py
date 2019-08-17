from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, current_user, login_user, logout_user, login_required, current_user

app = Flask(__name__, static_folder='client')

app.config.from_object(Config)
db = SQLAlchemy(app)
login_mgr = LoginManager(app)
Migrate(app, db)

from app import routes
