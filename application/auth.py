from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from .models import User
from . import db, login_manager, mail

auth = Blueprint('auth', __name__)

serializer = URLSafeTimedSerializer('your-secret-key')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_email(user):
    token = serializer.dumps(user.email, salt='email-confirm')
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = render_template('activate.html', confirm_url=confirm_url)
    subject = "Please confirm your email"
    message = Message(subject=subject, recipients=[user.email], html=html)
    mail.send(message)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    user = User(email=request.form['email'], password=request.form['password'])
    db.session.add(user)
    db.session.commit()
    send_email(user)
    login_user(user)
    return redirect(url_for('unconfirmed'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    email = request.form['email']
    password = request.form['password']
    registered_user = User.query.filter_by(email=email, password=password).first()
    if registered_user is None:
        return 'Username or Password is invalid', 401
    login_user(registered_user)
    return redirect(request.args.get('next') or url_for('home'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
