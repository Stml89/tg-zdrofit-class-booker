"""Helpers for matching upcoming booked trainings to filters with reminders.

These are pure functions (no I/O) so they are easy to unit-test. The scheduler
uses them to decide which upcoming classes should trigger a reminder and when.
"""

from datetime import datetime
from typing import List, Optional

from src.utils.helpers import parse_datetime


def _normalize(text: Optional[str]) -> str:
    """Lower-case and strip a string for lenient comparison."""
    return (text or "").strip().lower()


def _loose_match(a: Optional[str], b: Optional[str]) -> bool:
    """Return True if a and b are considered a match.

    Matching is lenient: equal, or one contains the other. If either side is
    empty, that criterion is treated as "not specified" and passes.
    """
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return True
    return na == nb or na in nb or nb in na


def class_matches_filter(class_item: dict, user_filter) -> bool:
    """Check whether a booked class (from the API schedule) matches a filter.

    Compares club name and class/timetable name. If the filter specifies a
    trainer, the trainer must match too.

    Args:
        class_item: Schedule item dict with keys like name, club, zone, trainer.
        user_filter: UserFilter object.

    Returns:
        True if the class matches the filter.
    """
    if not _loose_match(class_item.get("club"), getattr(user_filter, "club_name", None)):
        return False
    if not _loose_match(class_item.get("name"), getattr(user_filter, "timetable_name", None)):
        return False

    trainer_name = getattr(user_filter, "trainer_name", None)
    if _normalize(trainer_name):
        # Filter pins a specific trainer -> require a trainer match
        if not _loose_match(class_item.get("trainer"), trainer_name):
            return False

    return True


def find_reminder_filter(class_item: dict, filters: List) -> Optional[object]:
    """Find the best active filter (reminder enabled) matching a class.

    When multiple filters match, the one with the largest reminder lead time is
    chosen so the user is reminded as early as their settings allow.

    Args:
        class_item: Schedule item dict.
        filters: Iterable of UserFilter objects.

    Returns:
        The matching UserFilter with a reminder enabled, or None.
    """
    best = None
    for f in filters:
        reminder = getattr(f, "reminder_minutes", None)
        if not reminder:
            continue
        if getattr(f, "is_paused", False):
            continue
        if class_matches_filter(class_item, f):
            if best is None or reminder > best.reminder_minutes:
                best = f
    return best


def parse_reminder_time(start_time: str) -> Optional[datetime]:
    """Parse a schedule start_time into a naive local datetime.

    Timezone-aware values are converted to local time and made naive so they can
    be compared against ``datetime.now()`` (matching the rest of the codebase).
    """
    dt = parse_datetime(start_time)
    if dt is not None and dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def should_send_reminder(start_time: datetime, reminder_minutes: int, now: datetime) -> bool:
    """Return True if ``now`` is within the reminder window before the class.

    The window is ``[start_time - reminder_minutes, start_time)``: the reminder
    should fire once we are within ``reminder_minutes`` of the class but it has
    not started yet.
    """
    if start_time is None or not reminder_minutes:
        return False
    minutes_until = (start_time - now).total_seconds() / 60.0
    return 0 < minutes_until <= reminder_minutes
