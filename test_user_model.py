"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follow
from sqlalchemy import and_

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['WTF_CSRF_ENABLED'] = False

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

class UserModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        u3 = User.signup("u3", "u3@email.com", "password", None)

        u2.following.append(u3)

        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.u3_id = u3.id

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

    def test_user_authenticate_with_valid_username_password(self):
        """Tests successful user authentication"""

        u1 = User.query.get(self.u1_id)

        authenticated_user = User.authenticate(u1.username, "password")

        self.assertIsInstance(authenticated_user, User)

    def test_user_authenticate_with_invalid_username(self):
        """Tests user authentication with invalid username"""

        authenticated_user = User.authenticate("not_a_username", "password")

        self.assertIs(authenticated_user, False)

    def test_user_authenticate_with_invalid_password(self):
        """Tests user authentication with invalid password"""

        u1 = User.query.get(self.u1_id)

        authenticated_user = User.authenticate(u1.username, "not_the_right_pass")

        self.assertIs(authenticated_user, False)
