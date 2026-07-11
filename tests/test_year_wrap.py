"""Tests for the Year Wrap (Spotify-Wrapped style) yearly statistics feature."""

import sys
import os
import unittest
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User
from src.year_wrap import (
    YearWrapStats,
    compute_year_wrap,
    format_year_wrap_message,
    top_n,
    _personality,
    _to_local_naive,
    _class_duration_hours,
    _headline,
    _format_ranking,
    _format_delta,
    _longest_weekly_streak,
    _pluralize,
    NIGHT_OWL,
)


def _cls(name, trainer, start, end=None):
    """Build a schedule class dict like get_user_schedule() returns."""
    return {
        "name": name,
        "trainer": trainer,
        "start_time": start,
        "end_time": end,
    }


class TestTopN(unittest.TestCase):
    """Tests for the generic top_n helper."""

    def test_empty(self):
        self.assertEqual(top_n([]), [])

    def test_counts_and_order(self):
        items = ["Yoga", "Pilates", "Yoga", "Yoga", "Pilates", "Spin"]
        self.assertEqual(top_n(items, 3), [("Yoga", 3), ("Pilates", 2), ("Spin", 1)])

    def test_limit(self):
        items = ["a", "a", "b", "b", "c", "d"]
        result = top_n(items, 2)
        self.assertEqual(len(result), 2)

    def test_ignores_blank_and_none(self):
        items = ["Yoga", "", "   ", None, "Yoga"]
        self.assertEqual(top_n(items, 3), [("Yoga", 2)])

    def test_tie_break_alphabetical(self):
        items = ["banana", "apple"]
        # Equal counts -> alphabetical order
        self.assertEqual(top_n(items, 2), [("apple", 1), ("banana", 1)])

    def test_strips_whitespace(self):
        items = ["  Yoga  ", "Yoga"]
        self.assertEqual(top_n(items, 1), [("Yoga", 2)])


class TestHelpers(unittest.TestCase):
    """Tests for small pure helpers."""

    def test_to_local_naive_none(self):
        self.assertIsNone(_to_local_naive(None))
        self.assertIsNone(_to_local_naive("not-a-date"))

    def test_to_local_naive_naive_passthrough(self):
        dt = _to_local_naive("2026-06-24T10:00:00")
        self.assertEqual(dt, datetime(2026, 6, 24, 10, 0, 0))
        self.assertIsNone(dt.tzinfo)

    def test_to_local_naive_strips_tz(self):
        dt = _to_local_naive("2026-06-24T10:00:00+00:00")
        self.assertIsNone(dt.tzinfo)

    def test_class_duration_hours(self):
        item = _cls("Yoga", "T", "2026-01-01T10:00:00", "2026-01-01T11:30:00")
        self.assertAlmostEqual(_class_duration_hours(item), 1.5)

    def test_class_duration_missing_end(self):
        item = _cls("Yoga", "T", "2026-01-01T10:00:00", None)
        self.assertEqual(_class_duration_hours(item), 0.0)

    def test_class_duration_missing_start(self):
        item = _cls("Yoga", "T", None, "2026-01-01T11:00:00")
        self.assertEqual(_class_duration_hours(item), 0.0)

    def test_class_duration_negative_is_zero(self):
        item = _cls("Yoga", "T", "2026-01-01T11:00:00", "2026-01-01T10:00:00")
        self.assertEqual(_class_duration_hours(item), 0.0)

    def test_personality_none(self):
        self.assertIsNone(_personality([]))

    def test_personality_early_bird(self):
        self.assertIn("Early Bird", _personality([6, 7, 8, 18]))

    def test_personality_midday(self):
        self.assertIn("Midday", _personality([12, 13, 14]))

    def test_personality_after_work(self):
        self.assertIn("After-Work", _personality([18, 19, 20]))

    def test_personality_night_owl(self):
        self.assertEqual(_personality([23, 2, 3]), NIGHT_OWL)

    def test_headline_tiers(self):
        self.assertIn("Unstoppable", _headline(200))
        self.assertIn("Legend", _headline(100))
        self.assertIn("Fire", _headline(50))
        self.assertIn("Strong", _headline(20))
        self.assertIn("Habit", _headline(5))
        self.assertIn("Getting Started", _headline(1))

    def test_format_ranking_singular_plural(self):
        text = _format_ranking("Top", [("Yoga", 1), ("Spin", 2)], "time")
        self.assertIn("🥇 Yoga — 1 time", text)
        self.assertIn("🥈 Spin — 2 times", text)

    def test_format_ranking_class_plural(self):
        # "class" must pluralize to "classes", not "classs"
        text = _format_ranking("Top", [("Anna", 3)], "class")
        self.assertIn("Anna — 3 classes", text)
        self.assertNotIn("classs", text)

    def test_pluralize(self):
        self.assertEqual(_pluralize("class", 1), "class")
        self.assertEqual(_pluralize("class", 2), "classes")
        self.assertEqual(_pluralize("time", 2), "times")
        self.assertEqual(_pluralize("box", 2), "boxes")

    def test_format_ranking_beyond_medals(self):
        ranking = [("a", 5), ("b", 4), ("c", 3), ("d", 2)]
        text = _format_ranking("Top", ranking, "class")
        self.assertIn("4. d", text)

    def test_format_delta_none_when_no_prev(self):
        stats = YearWrapStats(year=2026, total_classes=10, prev_year_total=0)
        self.assertIsNone(_format_delta(stats))

    def test_format_delta_more(self):
        stats = YearWrapStats(year=2026, total_classes=20, prev_year_total=10)
        self.assertIn("10 more", _format_delta(stats))

    def test_format_delta_fewer(self):
        stats = YearWrapStats(year=2026, total_classes=5, prev_year_total=10)
        self.assertIn("5 fewer", _format_delta(stats))

    def test_format_delta_equal(self):
        stats = YearWrapStats(year=2026, total_classes=10, prev_year_total=10)
        self.assertIn("same", _format_delta(stats))


class TestLongestStreak(unittest.TestCase):
    """Tests for the _longest_weekly_streak helper."""

    def test_empty(self):
        self.assertEqual(_longest_weekly_streak([]), 0)

    def test_single_class(self):
        self.assertEqual(_longest_weekly_streak([datetime(2026, 1, 7, 10)]), 1)

    def test_two_consecutive_weeks(self):
        starts = [datetime(2026, 1, 7, 10), datetime(2026, 1, 13, 18)]
        # Jan 7 -> Monday Jan 5; Jan 13 -> Monday Jan 12 (7 days apart)
        self.assertEqual(_longest_weekly_streak(starts), 2)

    def test_same_week_counts_once(self):
        starts = [datetime(2026, 1, 5, 10), datetime(2026, 1, 8, 18)]
        # Both map to Monday Jan 5
        self.assertEqual(_longest_weekly_streak(starts), 1)

    def test_broken_streak_returns_longest_run(self):
        starts = [
            datetime(2026, 1, 5),   # Mon week Jan 5  (run start)
            datetime(2026, 1, 12),  # Mon week Jan 12 (run = 2)
            datetime(2026, 1, 26),  # Mon week Jan 26 (gap -> reset, run = 1)
            datetime(2026, 2, 2),   # Mon week Feb 2  (run = 2)
            datetime(2026, 2, 9),   # Mon week Feb 9  (run = 3)
        ]
        self.assertEqual(_longest_weekly_streak(starts), 3)

    def test_non_consecutive_isolated_weeks(self):
        starts = [datetime(2026, 1, 5), datetime(2026, 3, 2)]
        self.assertEqual(_longest_weekly_streak(starts), 1)

    def test_unsorted_input(self):
        starts = [datetime(2026, 1, 19), datetime(2026, 1, 5), datetime(2026, 1, 12)]
        self.assertEqual(_longest_weekly_streak(starts), 3)

    def test_cross_year_boundary(self):
        # Dec 29 2025 (Mon) and Jan 5 2026 (Mon) are exactly 7 days apart
        starts = [datetime(2025, 12, 29), datetime(2026, 1, 5)]
        self.assertEqual(_longest_weekly_streak(starts), 2)


class TestComputeYearWrap(unittest.TestCase):
    """Tests for the main compute_year_wrap aggregation."""

    def setUp(self):
        self.now = datetime(2026, 12, 31, 12, 0, 0)

    def test_no_classes_returns_none(self):
        self.assertIsNone(compute_year_wrap([], 2026, self.now))

    def test_future_classes_ignored(self):
        schedule = [_cls("Yoga", "Anna", "2026-12-31T18:00:00")]  # after now
        self.assertIsNone(compute_year_wrap(schedule, 2026, self.now))

    def test_other_year_ignored(self):
        schedule = [_cls("Yoga", "Anna", "2025-06-01T10:00:00")]
        self.assertIsNone(compute_year_wrap(schedule, 2026, self.now))

    def test_basic_counts(self):
        schedule = [
            _cls("Yoga", "Anna", "2026-01-10T10:00:00", "2026-01-10T11:00:00"),
            _cls("Yoga", "Anna", "2026-01-20T10:00:00", "2026-01-20T11:00:00"),
            _cls("Spin", "Bob", "2026-02-15T18:00:00", "2026-02-15T19:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(stats.total_classes, 3)
        self.assertEqual(stats.top_classes[0], ("Yoga", 2))
        self.assertEqual(stats.top_trainers[0], ("Anna", 2))
        self.assertAlmostEqual(stats.total_hours, 3.0)

    def test_top_three_only(self):
        schedule = [
            _cls("A", "T", "2026-01-01T10:00:00"),
            _cls("B", "T", "2026-01-02T10:00:00"),
            _cls("C", "T", "2026-01-03T10:00:00"),
            _cls("D", "T", "2026-01-04T10:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(len(stats.top_classes), 3)

    def test_top_months(self):
        schedule = [
            _cls("A", "T", "2026-03-01T10:00:00"),
            _cls("A", "T", "2026-03-05T10:00:00"),
            _cls("A", "T", "2026-07-01T10:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(stats.top_months[0], ("March", 2))
        self.assertIn(("July", 1), stats.top_months)

    def test_favorite_weekday(self):
        # 2026-01-05 is a Monday, 2026-01-12 is a Monday, 2026-01-06 is Tuesday
        schedule = [
            _cls("A", "T", "2026-01-05T10:00:00"),
            _cls("A", "T", "2026-01-12T10:00:00"),
            _cls("A", "T", "2026-01-06T10:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(stats.favorite_weekday, ("Monday", 2))

    def test_personality_in_stats(self):
        schedule = [_cls("A", "T", "2026-01-05T06:30:00")]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertIn("Early Bird", stats.personality)

    def test_longest_streak_in_stats(self):
        schedule = [
            _cls("A", "T", "2026-01-05T10:00:00"),  # Mon, week Jan 5
            _cls("A", "T", "2026-01-12T10:00:00"),  # Mon, week Jan 12 (consecutive)
            _cls("A", "T", "2026-01-19T10:00:00"),  # Mon, week Jan 19 (consecutive) -> 3
            _cls("A", "T", "2026-03-02T10:00:00"),  # isolated week
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(stats.longest_streak_weeks, 3)

    def test_prev_year_total(self):
        schedule = [
            _cls("A", "T", "2026-01-05T10:00:00"),
            _cls("A", "T", "2025-01-05T10:00:00"),
            _cls("A", "T", "2025-02-05T10:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(stats.total_classes, 1)
        self.assertEqual(stats.prev_year_total, 2)

    def test_missing_start_time_skipped(self):
        schedule = [
            _cls("A", "T", None),
            _cls("B", "T", "2026-01-05T10:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        self.assertEqual(stats.total_classes, 1)

    def test_default_now(self):
        # Use a past year so it works regardless of the real current date
        schedule = [_cls("A", "T", "2000-01-05T10:00:00")]
        stats = compute_year_wrap(schedule, 2000)
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_classes, 1)


class TestFormatMessage(unittest.TestCase):
    """Tests for the HTML message formatting."""

    def setUp(self):
        self.now = datetime(2026, 12, 31, 12, 0, 0)

    def test_message_contains_key_sections(self):
        schedule = [
            _cls("Yoga", "Anna", "2026-01-10T06:00:00", "2026-01-10T07:00:00"),
            _cls("Yoga", "Anna", "2026-01-12T06:00:00", "2026-01-12T07:00:00"),
            _cls("Spin", "Bob", "2026-02-15T18:00:00", "2026-02-15T19:00:00"),
            _cls("Spin", "Bob", "2025-02-15T18:00:00", "2025-02-15T19:00:00"),
        ]
        stats = compute_year_wrap(schedule, 2026, self.now)
        msg = format_year_wrap_message(stats)
        self.assertIn("2026 Fitness Wrapped", msg)
        self.assertIn("Top Classes", msg)
        self.assertIn("Top Trainers", msg)
        self.assertIn("Most Productive Months", msg)
        self.assertIn("Yoga", msg)
        self.assertIn("Anna", msg)
        # vs last year line present (prev_year_total = 1)
        self.assertIn("more", msg)
        # personality + weekday present
        self.assertIn("workout personality", msg)
        self.assertIn("go-to day", msg)
        # weekly streak present (Jan 5 & Jan 12 weeks are consecutive)
        self.assertIn("Longest streak: <b>2 weeks</b> in a row", msg)

    def test_message_singular_class(self):
        schedule = [_cls("Yoga", "Anna", "2026-01-10T10:00:00")]
        stats = compute_year_wrap(schedule, 2026, self.now)
        msg = format_year_wrap_message(stats)
        self.assertIn("1</b> class this year", msg)

    def test_message_without_prev_year(self):
        schedule = [_cls("Yoga", "Anna", "2026-01-10T10:00:00")]
        stats = compute_year_wrap(schedule, 2026, self.now)
        msg = format_year_wrap_message(stats)
        # No previous-year comparison lines
        self.assertNotIn("more than", msg)
        self.assertNotIn("fewer than", msg)

    def test_message_minimal_stats(self):
        # Degenerate stats (no rankings) should still render header/total/closing
        stats = YearWrapStats(
            year=2026,
            total_classes=0,
            top_classes=[],
            top_trainers=[],
            top_months=[],
            favorite_weekday=None,
            personality=None,
            total_hours=0.0,
            prev_year_total=0,
        )
        msg = format_year_wrap_message(stats)
        self.assertIn("2026 Fitness Wrapped", msg)
        self.assertNotIn("Top Classes", msg)
        self.assertNotIn("Top Trainers", msg)
        self.assertNotIn("Most Productive Months", msg)
        self.assertNotIn("go-to day", msg)
        self.assertNotIn("workout personality", msg)
        self.assertNotIn("Longest streak", msg)

    def test_message_includes_streak(self):
        stats = YearWrapStats(year=2026, total_classes=10, longest_streak_weeks=4)
        msg = format_year_wrap_message(stats)
        self.assertIn("Longest streak: <b>4 weeks</b> in a row", msg)

    def test_message_excludes_short_streak(self):
        # A streak of 1 week is not worth highlighting
        stats = YearWrapStats(year=2026, total_classes=3, longest_streak_weeks=1)
        msg = format_year_wrap_message(stats)
        self.assertNotIn("Longest streak", msg)


class TestYearWrapDatabase(unittest.TestCase):
    """Tests for year-wrap dedup database methods."""

    def setUp(self):
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)
        self.db.add_user(User(
            telegram_id=555,
            zdrofit_email="user@example.com",
            zdrofit_password="secret",
        ))

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_not_sent_initially(self):
        self.assertFalse(self.db.is_year_wrap_sent(555, 2026))

    def test_add_and_check(self):
        self.assertTrue(self.db.add_year_wrap_sent(555, 2026))
        self.assertTrue(self.db.is_year_wrap_sent(555, 2026))

    def test_per_year(self):
        self.db.add_year_wrap_sent(555, 2026)
        self.assertFalse(self.db.is_year_wrap_sent(555, 2025))

    def test_duplicate_ignored(self):
        self.db.add_year_wrap_sent(555, 2026)
        self.db.add_year_wrap_sent(555, 2026)
        self.assertTrue(self.db.is_year_wrap_sent(555, 2026))


class TestSchedulerYearWrap(unittest.IsolatedAsyncioTestCase):
    """Tests for the scheduler's per-user year-wrap sending."""

    def setUp(self):
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)
        self.db.add_user(User(
            telegram_id=777,
            zdrofit_email="user@example.com",
            zdrofit_password="secret",
        ))

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    async def test_sends_wrap_and_marks_sent(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        schedule = [
            _cls("Yoga", "Anna", "2000-01-10T10:00:00", "2000-01-10T11:00:00"),
            _cls("Yoga", "Anna", "2000-02-10T10:00:00", "2000-02-10T11:00:00"),
        ]
        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_user_schedule.return_value = schedule

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._send_user_year_wrap(777, "user@example.com", "secret", 2000)

        scheduler.notification_sender.send_year_wrap.assert_awaited_once()
        self.assertTrue(self.db.is_year_wrap_sent(777, 2000))

    async def test_dedup_skips_second_send(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        self.db.add_year_wrap_sent(777, 2000)
        mock_client = MagicMock()

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._send_user_year_wrap(777, "user@example.com", "secret", 2000)

        scheduler.notification_sender.send_year_wrap.assert_not_awaited()
        mock_client.authenticate.assert_not_called()

    async def test_auth_failure_no_send(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        mock_client = MagicMock()
        mock_client.authenticate.return_value = False

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._send_user_year_wrap(777, "user@example.com", "secret", 2000)

        scheduler.notification_sender.send_year_wrap.assert_not_awaited()
        self.assertFalse(self.db.is_year_wrap_sent(777, 2000))

    async def test_no_classes_marks_sent_without_message(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_user_schedule.return_value = []  # no classes

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._send_user_year_wrap(777, "user@example.com", "secret", 2000)

        scheduler.notification_sender.send_year_wrap.assert_not_awaited()
        self.assertTrue(self.db.is_year_wrap_sent(777, 2000))

    async def test_async_send_year_wraps_all_users(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()
        # Isolate iteration logic from the year/now-dependent per-user logic
        scheduler._send_user_year_wrap = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db):
            await scheduler._async_send_year_wraps()

        # One registered user -> per-user handler invoked exactly once
        scheduler._send_user_year_wrap.assert_awaited_once()
        # Called with the current year
        called_year = scheduler._send_user_year_wrap.call_args.args[3]
        self.assertEqual(called_year, datetime.now().year)

    async def test_async_send_year_wraps_no_users(self):
        from src.scheduler.class_scheduler import ClassCheckScheduler

        empty_db = MagicMock()
        empty_db.get_all_users.return_value = []

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", empty_db):
            await scheduler._async_send_year_wraps()

        scheduler.notification_sender.send_year_wrap.assert_not_awaited()


class TestWrappedCommand(unittest.IsolatedAsyncioTestCase):
    """Tests for the /wrapped Telegram command."""

    def _make_update(self):
        update = MagicMock()
        update.effective_user.id = 333
        update.message.reply_text = AsyncMock()
        return update

    async def test_not_logged_in(self):
        from src.telegram_bot.handlers import BotHandlers

        update = self._make_update()
        with patch("src.telegram_bot.handlers.db") as mock_db:
            mock_db.get_user.return_value = None
            await BotHandlers.wrapped(update, MagicMock())

        update.message.reply_text.assert_awaited_once()
        self.assertIn("login", update.message.reply_text.call_args.args[0].lower())

    async def test_auth_failure(self):
        from src.telegram_bot.handlers import BotHandlers

        update = self._make_update()
        mock_client = MagicMock()
        mock_client.authenticate.return_value = False

        with patch("src.telegram_bot.handlers.db") as mock_db, \
             patch("src.telegram_bot.handlers.ZdrofitAPIClient", return_value=mock_client):
            mock_db.get_user.return_value = MagicMock(
                zdrofit_email="e", zdrofit_password="p"
            )
            await BotHandlers.wrapped(update, MagicMock())

        self.assertIn("Authentication", update.message.reply_text.call_args.args[0])

    async def test_no_classes_message(self):
        from src.telegram_bot.handlers import BotHandlers

        update = self._make_update()
        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_user_schedule.return_value = []

        with patch("src.telegram_bot.handlers.db") as mock_db, \
             patch("src.telegram_bot.handlers.ZdrofitAPIClient", return_value=mock_client):
            mock_db.get_user.return_value = MagicMock(
                zdrofit_email="e", zdrofit_password="p"
            )
            await BotHandlers.wrapped(update, MagicMock())

        self.assertIn("haven't attended", update.message.reply_text.call_args.args[0])

    async def test_sends_wrap_message(self):
        from src.telegram_bot.handlers import BotHandlers

        update = self._make_update()
        year = datetime.now().year
        schedule = [
            _cls("Yoga", "Anna", f"{year}-01-10T10:00:00", f"{year}-01-10T11:00:00"),
        ]
        # Ensure the class is in the past relative to "now"
        schedule[0]["start_time"] = "2000-01-10T10:00:00"
        schedule[0]["end_time"] = "2000-01-10T11:00:00"

        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_user_schedule.return_value = schedule

        with patch("src.telegram_bot.handlers.db") as mock_db, \
             patch("src.telegram_bot.handlers.ZdrofitAPIClient", return_value=mock_client), \
             patch("src.telegram_bot.handlers.datetime") as mock_dt:
            mock_db.get_user.return_value = MagicMock(
                zdrofit_email="e", zdrofit_password="p"
            )
            mock_dt.now.return_value = datetime(2000, 12, 31, 12, 0, 0)
            await BotHandlers.wrapped(update, MagicMock())

        # The formatted wrap should have been sent with HTML
        sent_text = update.message.reply_text.call_args.args[0]
        self.assertIn("Fitness Wrapped", sent_text)


class TestNotificationSendYearWrap(unittest.IsolatedAsyncioTestCase):
    """Tests for NotificationSender.send_year_wrap."""

    async def test_send_year_wrap(self):
        from src.telegram_bot.notifications import NotificationSender

        sender = NotificationSender(bot=AsyncMock())
        await sender.send_year_wrap(123, "<b>hi</b>")
        sender.bot.send_message.assert_awaited_once()

    async def test_send_year_wrap_handles_error(self):
        from src.telegram_bot.notifications import NotificationSender

        bot = AsyncMock()
        bot.send_message.side_effect = Exception("boom")
        sender = NotificationSender(bot=bot)
        # Should not raise
        await sender.send_year_wrap(123, "x")


if __name__ == "__main__":
    unittest.main()
