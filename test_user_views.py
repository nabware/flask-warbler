"""User view tests."""

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


class UserViewTestCase(TestCase):
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

    def test_start_following(self):
        ''' Tests attribute updating for user following another user'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id


            response = c.post(f'/users/follow/{self.u2_id}', headers={
                    "referer" : "/"
            },follow_redirects=True)

            self.assertEqual(response.status_code,200)
            html = response.get_data(as_text=True)

            self.assertIn('<!-- HOMEPAGE :: FOR TESTING :: DO NOT MOVE -->',html)

            self.assertIsNotNone(
                Follow.query.filter(
                    and_(Follow.user_being_followed_id==self.u2_id,
                        Follow.user_following_id==self.u1_id)).one_or_none()
            )

    def test_stop_following(self):
        ''' Tests attribute updating for user unfollowing another user'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            response = c.post(
                f'/users/stop-following/{self.u3_id}',
                headers={
                    "referer" : "/"
                },
                follow_redirects=True
            )

            self.assertEqual(response.status_code,200)
            html = response.get_data(as_text=True)

            self.assertIn('<!-- HOMEPAGE :: FOR TESTING :: DO NOT MOVE -->',html)

            self.assertEqual(
                Follow.query.filter(
                and_(
                    Follow.user_being_followed_id==self.u3_id,
                    Follow.user_following_id==self.u2_id)
                ).count(),
                0
            )

    def test_follow_when_already_following(self):
        ''' Tests a case where a user tries to follow someone they
            already follow '''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id


            response = c.post(f'/users/follow/{self.u2_id}', headers={
                    "referer" : "/"
            })

            response = c.post(f'/users/follow/{self.u2_id}', headers={
                    "referer" : "/"
            },follow_redirects=True)

            self.assertEqual(response.status_code,200)
            html = response.get_data(as_text=True)

            self.assertIn('<!-- HOMEPAGE :: FOR TESTING :: DO NOT MOVE -->',html)
            self.assertIn("You are already following that user.",html)

            self.assertIsNotNone(
                Follow.query.filter(
                    and_(Follow.user_being_followed_id==self.u2_id,
                        Follow.user_following_id==self.u1_id)).one_or_none()
            )

    def test_unfollow_when_not_following(self):
        ''' Tests a case where a user tries to unfollow someone they
            are not following '''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            response = c.post(
                f'/users/stop-following/{self.u3_id}',
                headers={
                    "referer" : "/"
                },
                follow_redirects=True
            )

            response = c.post(
                f'/users/stop-following/{self.u3_id}',
                headers={
                    "referer" : "/"
                },
                follow_redirects=True
            )

            self.assertEqual(response.status_code,200)
            html = response.get_data(as_text=True)

            self.assertIn('<!-- HOMEPAGE :: FOR TESTING :: DO NOT MOVE -->',html)
            self.assertIn("You are not following that user.",html)

            self.assertEqual(
                Follow.query.filter(
                and_(
                    Follow.user_being_followed_id==self.u3_id,
                    Follow.user_following_id==self.u2_id)
                ).count(),
                0
            )

    def test_user_signup(self):
        """Tests successful user signup"""

        with app.test_client() as c:
            user_count = User.query.count()

            response = c.post(
                "/signup",
                data={
                "username": "test_user",
                "password": "password",
                "email": "test_user@gmail.com",
                },
                follow_redirects=True
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(User.query.count(), user_count + 1)
            self.assertEqual(
                User.query.filter_by(email="test_user@gmail.com").count(),
                1
            )

    def test_user_signup_with_invalid_username(self):
        """Tests user signup with already taken username"""

        with app.test_client() as c:
            user_count = User.query.count()

            response = c.post(
                "/signup",
                data={
                "username": "u1",
                "password": "password",
                "email": "another_test_email@gmail.com",
                },
                follow_redirects=True
            )

            html = response.get_data(as_text=True)
            self.assertIn("Username or email already taken",html)
            self.assertIn('<!-- SIGNUP PAGE :: FOR TESTING -->',html)
            self.assertEqual(response.status_code, 200)

            db.session.rollback()
            self.assertEqual(User.query.count(), user_count)

    def test_user_signup_with_invalid_email(self):
        """Tests user signup with already taken email"""

        with app.test_client() as c:
            user_count = User.query.count()

            response = c.post(
                "/signup",
                data={
                "username": "test_user",
                "password": "password",
                "email": "u1@email.com",
                },
                follow_redirects=True
            )

            html = response.get_data(as_text=True)
            self.assertIn("Username or email already taken",html)
            self.assertIn('<!-- SIGNUP PAGE :: FOR TESTING -->',html)
            self.assertEqual(response.status_code, 200)

            db.session.rollback()
            self.assertEqual(User.query.count(), user_count)

    def test_user_signup_with_invalid_password(self):
        """Tests user signup with invalid password"""

        with app.test_client() as c:
            user_count = User.query.count()

            response = c.post(
                "/signup",
                data={
                "username": "test_user",
                "password": "pa",
                "email": "another_test_email@email.com",
                },
                follow_redirects=True
            )

            html = response.get_data(as_text=True)
            self.assertIn("Field must be between 6 and 50 characters long.",html)
            self.assertIn('<!-- SIGNUP PAGE :: FOR TESTING -->',html)

            self.assertEqual(response.status_code, 200)
            db.session.rollback()
            self.assertEqual(User.query.count(), user_count)

    def test_user_signup_with_null_input(self):
        """Tests user signup with null input"""

        with app.test_client() as c:
            user_count = User.query.count()

            response = c.post(
                "/signup",
                data={
                "username": None,
                "password": "password",
                "email": "another_test_email@email.com",
                },
                follow_redirects=True
            )

            html = response.get_data(as_text=True)
            self.assertIn("This field is required.", html)
            self.assertIn('<!-- SIGNUP PAGE :: FOR TESTING -->', html)

            self.assertEqual(response.status_code, 200)
            db.session.rollback()
            self.assertEqual(User.query.count(), user_count)