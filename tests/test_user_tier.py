"""Tests for the free/paid user subscription tier (Step 1: DB foundation)."""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User


class TestUserTier(unittest.TestCase):
    """Tests for is_paid persistence and tier helper methods."""

    def setUp(self):
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def _add_user(self, telegram_id=100, is_paid=True):
        self.db.add_user(User(
            telegram_id=telegram_id,
            zdrofit_email=f"u{telegram_id}@example.com",
            zdrofit_password="secret",
            is_paid=is_paid,
        ))

    def test_default_user_is_paid(self):
        """New users default to the paid tier."""
        self._add_user(100)
        user = self.db.get_user(100)
        self.assertTrue(user.is_paid)

    def test_model_default_is_paid(self):
        """The User dataclass defaults is_paid to True."""
        user = User(telegram_id=1, zdrofit_email="e@x.com", zdrofit_password="p")
        self.assertTrue(user.is_paid)

    def test_add_free_user(self):
        """A user can be created on the free tier."""
        self._add_user(101, is_paid=False)
        user = self.db.get_user(101)
        self.assertFalse(user.is_paid)

    def test_is_user_paid(self):
        self._add_user(102, is_paid=True)
        self._add_user(103, is_paid=False)
        self.assertTrue(self.db.is_user_paid(102))
        self.assertFalse(self.db.is_user_paid(103))

    def test_is_user_paid_unknown(self):
        """Unknown users are treated as not paid."""
        self.assertFalse(self.db.is_user_paid(999999))

    def test_set_user_paid_upgrade(self):
        self._add_user(104, is_paid=False)
        self.assertTrue(self.db.set_user_paid(104, True))
        self.assertTrue(self.db.is_user_paid(104))

    def test_set_user_paid_downgrade(self):
        self._add_user(105, is_paid=True)
        self.assertTrue(self.db.set_user_paid(105, False))
        self.assertFalse(self.db.is_user_paid(105))

    def test_set_user_paid_unknown_returns_false(self):
        self.assertFalse(self.db.set_user_paid(888888, True))

    def test_tier_preserved_on_relogin(self):
        """Re-adding an existing user (re-login) must not reset their tier."""
        self._add_user(106, is_paid=False)
        # Simulate re-login: add_user called again (defaults is_paid=True)
        self.db.add_user(User(
            telegram_id=106,
            zdrofit_email="u106@example.com",
            zdrofit_password="secret",
        ))
        self.assertFalse(self.db.is_user_paid(106))

    def test_tier_in_get_all_users(self):
        self._add_user(107, is_paid=True)
        self._add_user(108, is_paid=False)
        users = {u.telegram_id: u for u in self.db.get_all_users()}
        self.assertTrue(users[107].is_paid)
        self.assertFalse(users[108].is_paid)


if __name__ == "__main__":
    unittest.main()
