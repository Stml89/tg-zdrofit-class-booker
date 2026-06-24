"""Tests for the training reminder feature."""

import sys
import os
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User, UserFilter
from src.reminders import (
    class_matches_filter,
    find_reminder_filter,
    parse_reminder_time,
    should_send_reminder,
)


# ----------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------
class TestUserFilterReminderField(unittest.TestCase):
    def test_reminder_minutes_default_none(self):
        f = UserFilter(user_id=1, club_id=7, club_name="Zdrofit")
        self.assertIsNone(f.reminder_minutes)

    def test_reminder_minutes_set(self):
        f = UserFilter(user_id=1, club_id=7, club_name="Zdrofit", reminder_minutes=30)
        self.assertEqual(f.reminder_minutes, 30)


# ----------------------------------------------------------------------------
# Matching helpers
# ----------------------------------------------------------------------------
class TestClassMatchesFilter(unittest.TestCase):
    def _filter(self, **kwargs):
        base = dict(user_id=1, club_id=7, club_name="Zdrofit Bemowo", timetable_name="Yoga")
        base.update(kwargs)
        return UserFilter(**base)

    def test_match_club_and_name(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga", "trainer": "Adam"}
        self.assertTrue(class_matches_filter(item, self._filter()))

    def test_match_case_insensitive_and_contains(self):
        item = {"club": "zdrofit bemowo dywizjonu", "name": "Power Yoga", "trainer": "Adam"}
        self.assertTrue(class_matches_filter(item, self._filter()))

    def test_no_match_different_club(self):
        item = {"club": "Zdrofit Mokotow", "name": "Yoga", "trainer": "Adam"}
        self.assertFalse(class_matches_filter(item, self._filter()))

    def test_no_match_different_class(self):
        item = {"club": "Zdrofit Bemowo", "name": "Pilates", "trainer": "Adam"}
        self.assertFalse(class_matches_filter(item, self._filter()))

    def test_trainer_required_when_specified(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga", "trainer": "Marek"}
        f = self._filter(trainer_name="Adam")
        self.assertFalse(class_matches_filter(item, f))

    def test_trainer_match_when_specified(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga", "trainer": "Adam Nowak"}
        f = self._filter(trainer_name="Adam")
        self.assertTrue(class_matches_filter(item, f))

    def test_any_trainer_when_not_specified(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga", "trainer": "Whoever"}
        self.assertTrue(class_matches_filter(item, self._filter()))


class TestFindReminderFilter(unittest.TestCase):
    def _filter(self, **kwargs):
        base = dict(user_id=1, club_id=7, club_name="Zdrofit Bemowo", timetable_name="Yoga")
        base.update(kwargs)
        return UserFilter(**base)

    def test_returns_matching_enabled_filter(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga"}
        f = self._filter(reminder_minutes=30)
        self.assertIs(find_reminder_filter(item, [f]), f)

    def test_ignores_disabled_filters(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga"}
        f = self._filter(reminder_minutes=None)
        self.assertIsNone(find_reminder_filter(item, [f]))

    def test_ignores_paused_filters(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga"}
        f = self._filter(reminder_minutes=30, paused_until=datetime.now() + timedelta(days=1))
        self.assertIsNone(find_reminder_filter(item, [f]))

    def test_ignores_non_matching(self):
        item = {"club": "Other Gym", "name": "Yoga"}
        f = self._filter(reminder_minutes=30)
        self.assertIsNone(find_reminder_filter(item, [f]))

    def test_picks_largest_reminder_window(self):
        item = {"club": "Zdrofit Bemowo", "name": "Yoga"}
        f15 = self._filter(reminder_minutes=15)
        f60 = self._filter(reminder_minutes=60)
        result = find_reminder_filter(item, [f15, f60])
        self.assertEqual(result.reminder_minutes, 60)


class TestParseReminderTime(unittest.TestCase):
    def test_parse_naive(self):
        dt = parse_reminder_time("2026-06-24T18:30:00")
        self.assertEqual(dt, datetime(2026, 6, 24, 18, 30, 0))

    def test_parse_tz_aware_made_naive(self):
        dt = parse_reminder_time("2026-06-24T18:30:00Z")
        self.assertIsNotNone(dt)
        self.assertIsNone(dt.tzinfo)

    def test_parse_invalid_returns_none(self):
        self.assertIsNone(parse_reminder_time("not-a-date"))

    def test_parse_none_returns_none(self):
        self.assertIsNone(parse_reminder_time(None))


class TestShouldSendReminder(unittest.TestCase):
    def test_within_window(self):
        now = datetime(2026, 6, 24, 18, 0, 0)
        start = now + timedelta(minutes=20)
        self.assertTrue(should_send_reminder(start, 30, now))

    def test_exactly_at_window_edge(self):
        now = datetime(2026, 6, 24, 18, 0, 0)
        start = now + timedelta(minutes=30)
        self.assertTrue(should_send_reminder(start, 30, now))

    def test_outside_window_too_early(self):
        now = datetime(2026, 6, 24, 18, 0, 0)
        start = now + timedelta(minutes=45)
        self.assertFalse(should_send_reminder(start, 30, now))

    def test_class_already_started(self):
        now = datetime(2026, 6, 24, 18, 0, 0)
        start = now - timedelta(minutes=5)
        self.assertFalse(should_send_reminder(start, 30, now))

    def test_reminder_disabled(self):
        now = datetime(2026, 6, 24, 18, 0, 0)
        start = now + timedelta(minutes=10)
        self.assertFalse(should_send_reminder(start, 0, now))

    def test_start_none(self):
        now = datetime(2026, 6, 24, 18, 0, 0)
        self.assertFalse(should_send_reminder(None, 30, now))


# ----------------------------------------------------------------------------
# Database persistence
# ----------------------------------------------------------------------------
class TestReminderDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)
        self.db.add_user(User(telegram_id=1, zdrofit_email="u@e.com", zdrofit_password="pw"))

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_filter_persists_reminder_minutes(self):
        self.db.add_filter(UserFilter(
            user_id=1, club_id=7, club_name="Zdrofit Bemowo",
            timetable_name="Yoga", reminder_minutes=30,
        ))
        filters = self.db.get_all_filters(1)
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0].reminder_minutes, 30)

    def test_filter_default_reminder_zero(self):
        self.db.add_filter(UserFilter(
            user_id=1, club_id=7, club_name="Zdrofit Bemowo", timetable_name="Yoga",
        ))
        filters = self.db.get_all_filters(1)
        self.assertFalse(filters[0].reminder_minutes)

    def test_get_filter_reads_reminder(self):
        self.db.add_filter(UserFilter(
            user_id=1, club_id=7, club_name="Zdrofit Bemowo",
            timetable_name="Yoga", reminder_minutes=60,
        ))
        f = self.db.get_filter(1)
        self.assertEqual(f.reminder_minutes, 60)

    def test_is_reminder_sent_initially_false(self):
        self.assertFalse(self.db.is_reminder_sent(1, "class_x"))

    def test_add_and_check_sent_reminder(self):
        self.assertTrue(self.db.add_sent_reminder(1, "class_x", 30))
        self.assertTrue(self.db.is_reminder_sent(1, "class_x"))

    def test_duplicate_sent_reminder_ignored(self):
        self.db.add_sent_reminder(1, "class_x", 30)
        self.db.add_sent_reminder(1, "class_x", 30)
        self.assertTrue(self.db.is_reminder_sent(1, "class_x"))

    def test_sent_reminder_per_user(self):
        self.db.add_user(User(telegram_id=2, zdrofit_email="b@e.com", zdrofit_password="pw"))
        self.db.add_sent_reminder(1, "class_x", 30)
        self.assertTrue(self.db.is_reminder_sent(1, "class_x"))
        self.assertFalse(self.db.is_reminder_sent(2, "class_x"))

    def test_integer_class_id_normalized(self):
        self.db.add_sent_reminder(1, 12345, 15)
        self.assertTrue(self.db.is_reminder_sent(1, "12345"))
        self.assertTrue(self.db.is_reminder_sent(1, 12345))


# ----------------------------------------------------------------------------
# Notification
# ----------------------------------------------------------------------------
class TestSendTrainingReminder(unittest.IsolatedAsyncioTestCase):
    async def test_reminder_contains_required_info(self):
        from src.telegram_bot.notifications import NotificationSender
        bot = AsyncMock()
        sender = NotificationSender(bot=bot)

        class_data = {
            "name": "Power Yoga",
            "club": "Zdrofit Bemowo",
            "zone": "Strefa A",
            "trainer": "Adam Nowak",
            "start_time": "2026-06-24T18:30:00",
        }
        await sender.send_training_reminder(123, class_data, 30)

        bot.send_message.assert_called_once()
        text = bot.send_message.call_args.kwargs["text"]
        self.assertIn("Power Yoga", text)            # training type
        self.assertIn("Zdrofit Bemowo", text)        # gym
        self.assertIn("Adam Nowak", text)            # trainer
        self.assertIn("24.06.2026 18:30", text)      # date & time
        self.assertIn("30 min", text)                # lead time

    async def test_reminder_handles_missing_fields(self):
        from src.telegram_bot.notifications import NotificationSender
        bot = AsyncMock()
        sender = NotificationSender(bot=bot)
        await sender.send_training_reminder(123, {}, 15)
        bot.send_message.assert_called_once()


# ----------------------------------------------------------------------------
# Scheduler integration
# ----------------------------------------------------------------------------
class TestSchedulerReminders(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)
        self.db.add_user(User(telegram_id=999, zdrofit_email="u@e.com", zdrofit_password="pw"))

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def _make_client(self, schedule):
        client = MagicMock()
        client.authenticate.return_value = True
        client.get_user_schedule.return_value = schedule
        return client

    async def test_reminder_sent_for_upcoming_class(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        self.db.add_filter(UserFilter(
            user_id=999, club_id=7, club_name="Zdrofit Bemowo",
            timetable_name="Yoga", reminder_minutes=30,
        ))
        start = (datetime.now() + timedelta(minutes=20)).replace(microsecond=0)
        schedule = [{
            "class_id": "c1", "name": "Yoga", "club": "Zdrofit Bemowo",
            "zone": "A", "trainer": "Adam", "start_time": start.isoformat(),
        }]
        client = self._make_client(schedule)

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=client):
            await scheduler._check_user_reminders(999, "u@e.com", "pw")

        scheduler.notification_sender.send_training_reminder.assert_called_once()
        args = scheduler.notification_sender.send_training_reminder.call_args.args
        self.assertEqual(args[0], 999)
        self.assertEqual(args[2], 30)
        self.assertTrue(self.db.is_reminder_sent(999, "c1"))

    async def test_reminder_not_sent_when_out_of_window(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        self.db.add_filter(UserFilter(
            user_id=999, club_id=7, club_name="Zdrofit Bemowo",
            timetable_name="Yoga", reminder_minutes=15,
        ))
        start = (datetime.now() + timedelta(hours=2)).replace(microsecond=0)
        schedule = [{
            "class_id": "c2", "name": "Yoga", "club": "Zdrofit Bemowo",
            "zone": "A", "trainer": "Adam", "start_time": start.isoformat(),
        }]
        client = self._make_client(schedule)

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=client):
            await scheduler._check_user_reminders(999, "u@e.com", "pw")

        scheduler.notification_sender.send_training_reminder.assert_not_called()
        self.assertFalse(self.db.is_reminder_sent(999, "c2"))

    async def test_reminder_not_duplicated(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        self.db.add_filter(UserFilter(
            user_id=999, club_id=7, club_name="Zdrofit Bemowo",
            timetable_name="Yoga", reminder_minutes=30,
        ))
        start = (datetime.now() + timedelta(minutes=20)).replace(microsecond=0)
        schedule = [{
            "class_id": "c3", "name": "Yoga", "club": "Zdrofit Bemowo",
            "zone": "A", "trainer": "Adam", "start_time": start.isoformat(),
        }]
        client = self._make_client(schedule)

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=client):
            await scheduler._check_user_reminders(999, "u@e.com", "pw")
            await scheduler._check_user_reminders(999, "u@e.com", "pw")

        self.assertEqual(scheduler.notification_sender.send_training_reminder.call_count, 1)

    async def test_no_api_call_when_no_reminder_filters(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        # Filter without reminder
        self.db.add_filter(UserFilter(
            user_id=999, club_id=7, club_name="Zdrofit Bemowo", timetable_name="Yoga",
        ))
        client = self._make_client([])

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=client) as mock_cls:
            await scheduler._check_user_reminders(999, "u@e.com", "pw")

        mock_cls.assert_not_called()  # short-circuits before constructing client
        scheduler.notification_sender.send_training_reminder.assert_not_called()


# ----------------------------------------------------------------------------
# Handler wizard step
# ----------------------------------------------------------------------------
class TestReminderHandler(unittest.IsolatedAsyncioTestCase):
    async def test_show_reminder_selection_sets_step_and_buttons(self):
        from src.telegram_bot import handlers
        context = MagicMock()
        context.user_data = {}
        query = AsyncMock()

        await handlers.show_reminder_selection(MagicMock(), context, 1, query)

        self.assertEqual(context.user_data["filter_step"], "reminder")
        query.edit_message_text.assert_called_once()
        markup = query.edit_message_text.call_args.kwargs["reply_markup"]
        callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        self.assertIn("filter_reminder_off", callbacks)
        self.assertIn("filter_reminder_15", callbacks)
        self.assertIn("filter_reminder_30", callbacks)
        self.assertIn("filter_reminder_60", callbacks)

    async def test_save_filter_persists_reminder(self):
        from src.telegram_bot import handlers
        context = MagicMock()
        context.user_data = {
            "filter_club_id": 7,
            "filter_club_name": "Zdrofit Bemowo",
            "filter_timetable_id": "20",
            "filter_timetable_name": "Yoga",
            "filter_trainer_id": None,
            "filter_trainer_name": None,
            "filter_time_from": None,
            "filter_time_to": None,
            "filter_time_hours": None,
            "filter_weekdays": None,
            "filter_auto_booking": False,
            "filter_reminder_minutes": 30,
        }
        query = AsyncMock()
        captured = {}

        def fake_add_filter(user_filter):
            captured["filter"] = user_filter
            return True

        with patch.object(handlers.db, "add_filter", side_effect=fake_add_filter):
            await handlers.save_filter_to_db(MagicMock(), context, 1, query)

        self.assertEqual(captured["filter"].reminder_minutes, 30)
        text = query.edit_message_text.call_args.args[0]
        self.assertIn("Reminder: 30 min", text)


if __name__ == "__main__":
    unittest.main()
