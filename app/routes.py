from flask import render_template, redirect, flash, url_for
from flask_login import login_user, logout_user, current_user

from app import app
from app.models import User
from forms import LoginForm


@app.route('/')
def hello():
    return render_template('base.html', title='Home')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(flask.url_for('hello'))
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
