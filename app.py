import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from werkzeug.exceptions import Unauthorized

from forms import UserAddForm, LoginForm, MessageForm, CSRFProtectedForm, UserEditForm
from models import db, connect_db, User, Message, DEFAULT_HEADER_IMAGE_URL, DEFAULT_IMAGE_URL

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_and_csrf_to_g():
    """If we're logged in, add curr user to Flask global.
       Sets global csrf_form field to our CSRF protection form"""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None

    g.csrf_form = CSRFProtectedForm()


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if g.user:
        flash("You must be logged out to view the signup page.", "warning")
        return redirect("/")

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username or email already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    if g.user:
        flash("You must be logged out to view the login page.", "warning")
        return redirect("/")

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data,
        )

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    if not g.user:
        flash("You are already logged out","warning")
        return redirect("/")

    form = g.csrf_form

    if not form.validate_on_submit():
        raise Unauthorized()

    do_logout()
    flash("Successfully logged out.", "success")

    return redirect("/")


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

       Redirect to previous page
    """

    form = g.csrf_form

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    elif not form.validate_on_submit():
        raise Unauthorized()

    followed_user = User.query.get_or_404(follow_id)

    if followed_user in g.user.following:
        flash("You are already following that user.", "danger")
        return redirect("/")


    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(request.referrer)


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

       Redirect to previous page
    """

    form = g.csrf_form

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    elif not form.validate_on_submit():
        raise Unauthorized()

    followed_user = User.query.get_or_404(follow_id)

    if followed_user not in g.user.following:
        flash("You are not following that user.", "danger")
        return redirect("/")

    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(request.referrer)


@app.route('/users/profile', methods=["GET", "POST"])
def edit_profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserEditForm(obj=g.user)

    if form.validate_on_submit():
        if not User.authenticate(g.user.username, form.password.data):
            flash("Invalid password", "danger")
            return render_template("/users/edit.html", form=form)

        g.user.username = form.username.data or g.user.username
        g.user.email = form.email.data or g.user.email
        g.user.image_url = form.image_url.data or DEFAULT_IMAGE_URL
        g.user.header_image_url = form.header_image_url.data or DEFAULT_HEADER_IMAGE_URL
        g.user.bio = form.bio.data or g.user.bio

        db.session.commit()

        flash("User profile successfully updated!", "success")

        return redirect(f"/users/{g.user.id}")

    return render_template("/users/edit.html", form=form)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    form = g.csrf_form

    if not g.user or not form.validate_on_submit():

        raise Unauthorized()

    do_logout()

    User.query.filter_by(id=g.user.id).delete()
    db.session.commit()
    flash("Account successfully deleted.","success")
    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    form = g.csrf_form

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    elif not form.validate_on_submit():
        raise Unauthorized()

    msg = Message.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")

##############################################################################
# Likes

@app.post('/messages/<int:message_id>/like')
def like_message(message_id):
    """Like a message.
    """
    # note if you dont use AJAX: browsers may disable referrer header.
    # include hidden input tag with form with 'referrer' information

    form = g.csrf_form
    msg = Message.query.get_or_404(message_id)

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    elif msg in g.user.liked_messages:
        flash("You have already liked this message", "danger")
        return redirect(request.referrer)

    elif msg.user.id == g.user.id:
        flash("You can't like your own message","danger")
        return redirect(request.referrer)

    elif not form.validate_on_submit():
        raise Unauthorized()

    g.user.liked_messages.append(msg)

    db.session.commit()

    flash("You liked this warble!", "success")

    return redirect(request.referrer)

@app.post('/messages/<int:message_id>/unlike')
def unlike_message(message_id):
    """Unlike a message.
    """

    msg = Message.query.get_or_404(message_id)
    form = g.csrf_form

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    elif msg not in g.user.liked_messages:
        flash("This message is not in your likes", "danger")
        return redirect(request.referrer)

    elif not form.validate_on_submit():
        raise Unauthorized()

    g.user.liked_messages.remove(msg)

    db.session.commit()

    flash("You unliked this warble!", "success")

    # return redirect(f"/messages/{message_id}")
    return redirect(request.referrer)

@app.get("/users/<int:user_id>/likes")
def show_user_likes(user_id):
    ''' Displays a list of liked messages for a given user'''

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/likes.html', user=user)




##############################################################################
# Homepage and error pages


@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of self & followed_users
    """

    if g.user:
        messages = (Message
                    .query
                    .filter(or_
                        (Message.user_id.in_(user.id for user in g.user.following),
                        (Message.user_id == g.user.id)))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
