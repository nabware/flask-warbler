"""Message Model tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_model.py


import os
from unittest import TestCase
from datetime import datetime

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)
        db.session.add_all([m1])
        db.session.commit()

        self.u1_id = u1.id
        self.m1_id = m1.id

    def test_timestamp(self):
        ''' Tests that timestamps are being added to messages
            by comparing the timestamps of two messages'''
        m1 = Message.query.get(self.m1_id)
        m2 = Message(text="m2-text", user_id=self.u1_id)
        db.session.add(m2)
        db.session.commit()

        self.assertLess(m1.timestamp,m2.timestamp)
        self.assertIsInstance(m1.timestamp,datetime)
