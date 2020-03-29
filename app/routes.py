from flask import render_template, redirect, flash, url_for, request, abort, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app import app
from app.models import User
from app.forms import LoginForm


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


@app.route('/')
def lobby():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('lobby.html')

global_chat_messages = []

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

    return jsonify([{'index': index, 'user': user, 'message': message}
        for index, (user, message) in enumerate(global_chat_messages[first:], first)])
