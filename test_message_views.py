"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User, Like
from sqlalchemy import and_

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


class MessageBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)
        m2 = Message(text="m2-text", user_id=u2.id)


        db.session.add_all([m1,m2])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id
        self.m2_id = m2.id

    def tearDown(self):
        db.session.rollback()

class MessageAddDeleteViewTestCase(MessageBaseViewTestCase):
    """Tests message add and delete cases"""
    #TODO: seperate adding and deleting into seperate classes. put delete on bottom

    def test_add_message(self):
        """Tests adding message"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            Message.query.filter_by(text="Hello").one()

    def test_add_message_when_logged_out(self):
        """Tests adding message when logged out"""

        with app.test_client() as c:
            # Now, that session setting is saved, so we can have
            # the rest of ours test
            #TODO: generally, follow redirects through. when testing views, check resulting html
            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            self.assertIsNone(
                Message.query.filter_by(text="Hello").one_or_none()
            )

    def test_delete_message(self):
        ''' Tests the deletion of a message '''
        #TODO: check for flash message
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/messages/{self.m1_id}/delete")

            self.assertEqual(resp.status_code, 302)

            self.assertEqual(Message.query.get(self.m1_id),None)

    def test_delete_message_when_logged_out(self):
        """Tests deleting message when logged out"""
        #TODO: check for flash message
        with app.test_client() as c:
            resp = c.post(f"/messages/{self.m1_id}/delete")

            self.assertEqual(resp.status_code, 302)

            self.assertIsNotNone(Message.query.get(self.m1_id))

    def test_delete_other_users_message(self):
        ''' Tests deleting another users message '''
        #TODO: check for flash message
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/messages/{self.m2_id}/delete")

            self.assertEqual(resp.status_code, 302)

            self.assertIsNotNone(Message.query.get(self.m2_id))

    def test_show_message(self):
        ''' Test the display of an individual message'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f"/messages/{self.m1_id}",follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("m1-text",html)

class MessageLikeUnlikeViewTestCase(MessageBaseViewTestCase):
    """Tests message like and unlike cases"""
    #TODO: check user follower/following test patterns and move here
    #TODO: check heart filled in icon
    def test_like_message(self):
        ''' Tests the ability of a user to like a message'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/messages/{self.m2_id}/like")

            self.assertEqual(resp.status_code, 302)

            self.assertEqual(
                Like.query.filter(
                and_(
                    Like.message_id==self.m2_id,
                    Like.user_id==self.u1_id)
                ).count(),
                1
            )

    def test_like_own_message(self):
        ''' Tests that a user cannot like their own message'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(
                f"/messages/{self.m1_id}/like",
                follow_redirects=True,
                headers={'referer': '/'}
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("You can&#39;t like your own message", html)

            self.assertEqual(
                Like.query.filter(
                and_(
                    Like.message_id==self.m1_id,
                    Like.user_id==self.u1_id)
                ).count(),
                0
            )

    def test_unlike_message(self):
        ''' Tests the ability of a user to unlike a message'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/messages/{self.m2_id}/like")

            resp = c.post(f"/messages/{self.m2_id}/unlike")

            self.assertEqual(resp.status_code, 302)

            self.assertEqual(
                Like.query.filter(
                and_(
                    Like.message_id==self.m2_id,
                    Like.user_id==self.u1_id)
                ).count(),
                0
            )

    def test_unlike_unliked_message(self):
        ''' Tests the ability of a user to unlike a message'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/messages/{self.m2_id}/unlike",
                          follow_redirects=True,
                          headers={'referer': '/'})

            html= resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("This message is not in your likes", html)

            self.assertEqual(
                Like.query.filter(
                and_(
                    Like.message_id==self.m2_id,
                    Like.user_id==self.u1_id)
                ).count(),
                0
            )

    def test_user_likes_page(self):
        ''' Tests the user likes page'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/messages/{self.m2_id}/like")
            resp = c.get(f"/users/{self.u1_id}/likes")
            html = resp.get_data(as_text=True)

            self.assertIn("LIKES PAGE :: FOR TESTING", html)
            self.assertIn("m2-text", html)
