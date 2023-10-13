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
        u4 = User.signup("UNIQUE_USER_NAME_FOR_TEST", "u4@email.com", "password", None)

        u2.following.append(u3)
        u4.following.append(u3)
        u3.following.append(u4)

        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.u3_id = u3.id
        self.u4_id = u4.id

    def tearDown(self):
        db.session.rollback()

class FollowTestCase(UserViewTestCase):
    """Tests follow cases"""

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

    def test_follower_page_updating(self):
        ''' Tests that when a user follows someone, that user
            shows up in the followed user's followers page'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        response = c.post(f'/users/follow/{self.u2_id}', headers={
                "referer" : "/"
        })

        response = c.get(f'/users/{self.u2_id}/followers')
        html = response.get_data(as_text=True)
        self.assertIn("u1",html)

    def test_following_page_updating(self):
        ''' Tests that when a user follows someone, that user
            shows up in the user's following page'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        response = c.post(f'/users/follow/{self.u2_id}', headers={
                "referer" : "/"
        })

        response = c.get(f'/users/{self.u1_id}/following')
        html = response.get_data(as_text=True)
        self.assertIn("u2",html)

    def test_follower_page_updating_when_unfollowed(self):
        ''' Tests that when a user unfollows someone, that user does not
            show up in the followed user's followers page'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u4_id

        response = c.post(f'/users/stop-following/{self.u3_id}')
        response = c.get(f'/users/{self.u3_id}/followers')

        html = response.get_data(as_text=True)
        self.assertNotIn("<p>@UNIQUE_USER_NAME_FOR_TEST</p>",html)

    def test_following_page_updating_when_unfollowed(self):
        ''' Tests that when a user unfollows someone, that user does not
            show up in the previously followed user's following page'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u3_id

        response = c.post(f'/users/stop-following/{self.u4_id}')
        response = c.get(f'/users/{self.u3_id}/following')

        html = response.get_data(as_text=True)
        self.assertNotIn("<p>@UNIQUE_USER_NAME_FOR_TEST</p>",html)

class SignupTestCase(UserViewTestCase):
    """Tests signup cases"""

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

class AuthorizationTestCase(UserViewTestCase):
    """Tests access for both users and non-users """

    def test_view_followers_page(self):
        ''' Tests visiting another users followers page'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            response = c.get(f"/users/{self.u2_id}/followers")

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertNotIn('Access unauthorized.', html)
            self.assertIn('FOLLOWERS PAGE :: FOR TESTING', html)

    def test_view_following_page(self):
        ''' Tests visiting another users following pages'''

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            response = c.get(f"/users/{self.u2_id}/following")

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertNotIn('Access unauthorized.', html)
            self.assertIn('FOLLOWING PAGE :: FOR TESTING', html)

    def test_view_followers_page_when_logged_out(self):
        ''' Tests visiting users followers page when logged out'''

        with app.test_client() as c:
            response = c.get(f"/users/{self.u1_id}/followers",
                             follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertIn('Access unauthorized.', html)
            self.assertNotIn('FOLLOWERS PAGE :: FOR TESTING', html)

    def test_view_following_page_when_logged_out(self):
        ''' Tests visiting users following pages when logged out'''

        with app.test_client() as c:
            response = c.get(f"/users/{self.u1_id}/following",
                             follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertIn('Access unauthorized.', html)
            self.assertNotIn('FOLLOWING PAGE :: FOR TESTING', html)

