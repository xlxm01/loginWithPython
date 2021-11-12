# -*- coding: iso-8859-15 -*-
__author__ = 'Laura Murillo'


from flask import Flask, request, render_template, session, redirect, url_for
import os.path
from os import listdir
import json
from time import time
import sys

app = Flask(__name__)

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    """
    It process '/' and '/index' urls.
    :return: content of index.html file
    """
    if 'user_name' in session:
        logged = True
        nickname = session['user_name']
    else:
        logged = False
        nickname = ''
    return render_template('index.html', logged=logged, nickname=nickname)


@app.route('/home', methods=['GET', 'POST'])
def home():
    """
    It process '/home' url (main app page)
    :return: if everything is fine, content of home.html file
    """
    if 'user_name' not in session:
        return process_error("you must be logged to use the app / debe registrarse antes de usar la aplicacion",
                             url_for("login"))
    if request.method == 'POST' and request.form['message'] != "":
        messages = session['messages']
        if not messages:
            messages = []
        messages.append((time(), request.form['message']))
        save_current_user()
    else:  # The http GET method was used
        messages = session['messages']
    session['messages'] = messages
    return render_template('home.html', logged=True, nickname=session['user_name'], messages=messages,
                           friends_messages=sorted(get_friends_messages_with_authors(), key=lambda x: x[1]))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """
    It process '/profile' url (showing user data)
    :return: if user is logged, content of file edit_profile.html
    """
    if 'user_name' not in session:
        return process_error("you must be logged to use the app / debe registrarse antes de usar la aplicacion",
                             url_for("login"))
    if request.method == 'POST':
        session['user_name'] = request.form['nickname']
        session['password'] = request.form['passwd']
        session['friends'] = [str.strip(str(friend)) for friend in request.form.getlist('friends')]
        return redirect(url_for("home"))
    else:  # The http GET method was used
        return render_template("edit_profile.html", nickname=session['user_name'], email=session['email'],
                               passwd=session['password'], friends= session['friends'],
                               all_users=get_all_users(session['email']))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    It process '/login' url (form for login into the system)
    :return: firstly it will render the page for filling out the login data. Afterwards it will process these data.
    """
    if request.method == 'POST':
        missing = []
        fields = ['email', 'passwd', 'login_submit']
        for field in fields:
            value = request.form.get(field, None)
            if value is None or value == '':
                missing.append(field)
        if missing:
            return render_template('missingFields.html', inputs=missing, next=url_for("login"))

        return load_user(request.form['email'], request.form['passwd'])

    return app.send_static_file('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    It process '/signup' url (form for creating a new user)
    :return: firstly it will render the page for filling out the new user data. Afterwards it will process these data.
    """
    if request.method == 'POST':
        return process_signup()

    # The http GET method was used
    return app.send_static_file('signup.html')


@app.route('/logout', methods=['GET', 'POST'])
def process_logout():
    """
    It process '/logout' url (user going out of the system)
    :return: the initial app page
    """
    save_current_user()
    session.pop('user_name', None)
    return redirect(url_for('index'))


#
#  internal auxiliary functions
#

def process_signup():
    faltan = []
    campos = ['nickname', 'email', 'passwd', 'confirm', 'signup_submit']
    for campo in campos:
        value = request.form.get(campo, None)
        if value is None or value == '':
            faltan.append(campo)
    if faltan:
        return render_template("missingFields.html", inputs=faltan, next=url_for("signup"))
    return create_user_file(request.form['nickname'], request.form['email'], request.form['passwd'], request.form['confirm'])


def process_error(message, next_page):
    """

    :param message:
    :param next_page:
    :return:
    """
    return render_template("error.html", error_message=message, next=next_page)


def load_user(email, passwd):
    """
    It loads data for the given user (identified by email) from the data directory.
    It looks for a file whose name matches the user email
    :param email: user id
    :param passwd: password to check in order to validate the user
    :return: content of the home page (app basic page) if user exists and password is correct
    """
    file_path = os.path.join(SITE_ROOT, "data/", email)
    if not os.path.isfile(file_path):
        return process_error("User not found / No existe un usuario con ese nombre", url_for("login"))
    with open(file_path, 'r') as f:
        data = json.load(f)
    if data['password'] != passwd:
        return process_error("Incorrect password / la clave no es correcta", url_for("login"))
    session['user_name'] = data['user_name']
    session['messages'] = data['messages']
    session['password'] = passwd
    session['email'] = email
    session['friends'] = data['friends']
    return redirect(url_for("home"))


def save_current_user():
    datos = {
        "user_name": session["user_name"],
        "password": session['password'],
        "messages": session['messages'], # lista de tuplas (time_stamp, mensaje)
        "email": session['email'],
        "friends": session['friends']
    }
    file_path = os.path.join(SITE_ROOT, "data/", session['email'])
    with open(file_path, 'w') as f:
        json.dump(datos, f)


def create_user_file(name, email, passwd, passwd_confirmation):
    """
    It creates the file (in the /data directory) for storing user data. The file name will match the user email.
    If the file already exists, it returns an error.
    If the password does not match the confirmation, it returns an error.
    :param name: Name or nickname of the user
    :param email: user email, which will be later used for retrieving data
    :param passwd: password for future logins
    :param passwd_confirmation: confirmation, must match the password
    :return: if no error is found, it sends the user to the home page
    """

    directory = os.path.join(SITE_ROOT, "data")
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(SITE_ROOT, "data/", email)
    if os.path.isfile(file_path):
        return process_error("The email is already used, you must select a different email / Ya existe un usuario con ese nombre",
                             url_for("signup"))
    if passwd != passwd_confirmation:
        return process_error("Your password and confirmation password do not match / Las claves no coinciden",
                             url_for("signup"))
    datos = {
        "user_name": name,
        "password": passwd,
        "messages": [],
        "friends": []
    }
    with open(file_path, 'w') as f:
        json.dump(datos, f)
    session['user_name'] = name
    session['password'] = passwd
    session['messages'] = []
    session['friends'] = []
    session['email'] = email
    return redirect(url_for("home"))


def get_friends_messages_with_authors():
    """
    Get all the message from those users followed by the current one (extracted from the session)
    :return: list of message, each with the form (user, time stamp, message)
    """
    message_and_authors = []
    for friend in session['friends']:
        texts = load_messages_from_user(friend)
        message_and_authors.extend(texts)
    return message_and_authors


def load_messages_from_user(user):
    """
    Get all the message stored for the given user
    :param user: the user whose message will be returned
    :return: all the message published by the given user as a list of (user, time stamp, message)
    """
    file_path = os.path.join(SITE_ROOT, "data/", user)
    if not os.path.isfile(file_path):
        return []
    with open(file_path, 'r') as f:
        data = json.load(f)
    messages_with_author = [(data["user_name"], message[0], message[1]) for message in data["messages"]]
    return messages_with_author


def get_all_users(user):
    """
    Get all the users that a given user (parameter) can select to follow
    :param user: current user to whom possible friends will be shown
    :return: the complete list of registered users, taking out the current one
    """
    dir_path = os.path.join(SITE_ROOT, "data/")
    user_list = listdir(dir_path)
    user_list.remove(user)
    return user_list


app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'  # this string is used for security reasons (see CSRF)
# todo: <-- explicar CSRF

# start the server with the 'run()' method
if __name__ == '__main__':
    if sys.platform == 'darwin' or sys.platform == 'linux':  # different port if running on Windows
        app.run(debug=True, port=8080)
    else:
        app.run(debug=True, port=80)
