"""Year Wrap — Spotify-Wrapped style yearly statistics for users.

These are pure functions (no I/O) so they're easy to unit-test. The scheduler
(every 31st of December) and the ``/wrapped`` command use them to build a
personalized year-in-review message from the user's booked-class schedule.

A class counts towards a year if it is a *past* class (``start_time`` before
``now``) whose ``start_time`` falls in that calendar year. This matches the
"attended classes" definition used by the milestones feature.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from src.utils.helpers import parse_datetime


DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# Workout-personality buckets keyed by (inclusive start hour, exclusive end hour)
PERSONALITY_BUCKETS = [
    (5, 11, "🌅 Early Bird"),
    (11, 17, "☀️ Midday Mover"),
    (17, 22, "🌆 After-Work Warrior"),
]
NIGHT_OWL = "🌙 Night Owl"


@dataclass
class YearWrapStats:
    """Aggregated yearly statistics for a single user."""

    year: int
    total_classes: int
    top_classes: List[Tuple[str, int]] = field(default_factory=list)
    top_trainers: List[Tuple[str, int]] = field(default_factory=list)
    top_months: List[Tuple[str, int]] = field(default_factory=list)
    favorite_weekday: Optional[Tuple[str, int]] = None
    personality: Optional[str] = None
    total_hours: float = 0.0
    prev_year_total: int = 0
    longest_streak_weeks: int = 0


def _to_local_naive(start_time: Optional[str]) -> Optional[datetime]:
    """Parse an ISO start_time into a naive local datetime (or None).

    Timezone-aware values are converted to local time and stripped of tzinfo so
    they can be compared against ``datetime.now()`` like the rest of the codebase.
    """
    dt = parse_datetime(start_time)
    if dt is not None and dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def _class_duration_hours(class_item: Dict) -> float:
    """Return the class duration in hours from start/end time, or 0.0."""
    start = _to_local_naive(class_item.get("start_time"))
    end = _to_local_naive(class_item.get("end_time"))
    if start is None or end is None:
        return 0.0
    seconds = (end - start).total_seconds()
    if seconds <= 0:
        return 0.0
    return seconds / 3600.0


def top_n(items: List[str], n: int = 3) -> List[Tuple[str, int]]:
    """Return the ``n`` most common non-empty values as (value, count) pairs.

    Ties are broken by first appearance, then alphabetically, for stable output.
    """
    cleaned = [str(i).strip() for i in items if i and str(i).strip()]
    counts = Counter(cleaned)
    # Sort by count desc, then value asc for deterministic ordering on ties.
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ordered[:n]


def _personality(hours: List[int]) -> Optional[str]:
    """Pick a workout-personality label from the hours classes started at."""
    if not hours:
        return None
    bucket_counts: Counter = Counter()
    for hour in hours:
        label = NIGHT_OWL
        for start, end, name in PERSONALITY_BUCKETS:
            if start <= hour < end:
                label = name
                break
        bucket_counts[label] += 1
    # Most common bucket; deterministic tie-break by label.
    return sorted(bucket_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _longest_weekly_streak(starts: List[datetime]) -> int:
    """Return the longest run of consecutive weeks the user trained.

    Each datetime is mapped to the Monday of its week; the streak is the maximum
    number of consecutive weeks (Mondays exactly 7 days apart) attended. Multiple
    classes in the same week count once. This is robust across year boundaries
    because it compares actual calendar dates rather than ISO week numbers.
    """
    if not starts:
        return 0
    mondays = sorted({(dt - timedelta(days=dt.weekday())).date() for dt in starts})
    longest = current = 1
    for prev, curr in zip(mondays, mondays[1:]):
        if (curr - prev).days == 7:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _attended_in_year(schedule: List[Dict], year: int, now: datetime) -> List[Dict]:
    """Return past classes whose start_time falls within ``year``."""
    attended = []
    for class_item in schedule:
        start = _to_local_naive(class_item.get("start_time"))
        if start is None:
            continue
        if start < now and start.year == year:
            attended.append(class_item)
    return attended


def _count_prev_year(schedule: List[Dict], year: int, now: datetime) -> int:
    """Count past classes attended in the previous calendar year."""
    return len(_attended_in_year(schedule, year - 1, now))


def compute_year_wrap(
    schedule: List[Dict],
    year: int,
    now: Optional[datetime] = None,
) -> Optional[YearWrapStats]:
    """Compute year-wrap statistics from a user's schedule.

    Args:
        schedule: List of class dicts (from ``get_user_schedule``) with keys
            like ``name``, ``trainer``, ``start_time``, ``end_time``.
        year: Calendar year to summarize.
        now: Reference "current" time (defaults to ``datetime.now()``); only
            classes that already started are counted.

    Returns:
        A :class:`YearWrapStats`, or ``None`` if the user attended no classes
        in ``year`` (nothing worth celebrating, so callers can skip sending).
    """
    if now is None:
        now = datetime.now()

    attended = _attended_in_year(schedule, year, now)
    if not attended:
        return None

    names: List[str] = []
    trainers: List[str] = []
    month_indices: List[int] = []
    weekday_indices: List[int] = []
    start_hours: List[int] = []
    start_dates: List[datetime] = []
    total_hours = 0.0

    for class_item in attended:
        names.append(class_item.get("name") or "")
        trainers.append(class_item.get("trainer") or "")
        # start_time is guaranteed parseable here (filtered by _attended_in_year)
        start = _to_local_naive(class_item.get("start_time"))
        month_indices.append(start.month)
        weekday_indices.append(start.weekday())
        start_hours.append(start.hour)
        start_dates.append(start)
        total_hours += _class_duration_hours(class_item)

    # Top 3 months (translate month number -> name)
    month_counts = top_n([MONTH_NAMES[m - 1] for m in month_indices], 3)

    # Favorite weekday (single best) — attended is non-empty, so always present
    favorite_weekday = top_n([DAY_NAMES[w] for w in weekday_indices], 1)[0]

    return YearWrapStats(
        year=year,
        total_classes=len(attended),
        top_classes=top_n(names, 3),
        top_trainers=top_n(trainers, 3),
        top_months=month_counts,
        favorite_weekday=favorite_weekday,
        personality=_personality(start_hours),
        total_hours=round(total_hours, 1),
        prev_year_total=_count_prev_year(schedule, year, now),
        longest_streak_weeks=_longest_weekly_streak(start_dates),
    )


def _headline(total: int) -> str:
    """Return a fun headline title based on how many classes were attended."""
    if total >= 200:
        return "🌟 Absolutely Unstoppable"
    if total >= 100:
        return "🏆 Fitness Legend"
    if total >= 50:
        return "🔥 On Fire"
    if total >= 20:
        return "💪 Strong & Steady"
    if total >= 5:
        return "🌱 Building the Habit"
    return "👋 Just Getting Started"


def _pluralize(unit: str, count: int) -> str:
    """Return the correctly pluralized ``unit`` for ``count`` items."""
    if count == 1:
        return unit
    if unit.endswith(("s", "x", "z", "ch", "sh")):
        return unit + "es"  # class -> classes
    return unit + "s"       # time -> times


def _format_ranking(title: str, ranking: List[Tuple[str, int]], unit: str) -> str:
    """Format a Top-N ranking block, e.g. medals + counts."""
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"<b>{title}</b>"]
    for idx, (value, count) in enumerate(ranking):
        medal = medals[idx] if idx < len(medals) else f"{idx + 1}."
        lines.append(f"{medal} {value} — {count} {_pluralize(unit, count)}")
    return "\n".join(lines)


def _format_delta(stats: YearWrapStats) -> Optional[str]:
    """Format the comparison-to-last-year line, or None if no prior data."""
    if stats.prev_year_total <= 0:
        return None
    delta = stats.total_classes - stats.prev_year_total
    if delta > 0:
        return f"📈 That's <b>{delta} more</b> than in {stats.year - 1}. Keep climbing!"
    if delta < 0:
        return f"📉 {abs(delta)} fewer than in {stats.year - 1} — let's bounce back in {stats.year + 1}!"
    return f"➖ Exactly the same as {stats.year - 1}. Rock-solid consistency!"


def format_year_wrap_message(stats: YearWrapStats) -> str:
    """Build the HTML Telegram message for a user's year wrap."""
    parts: List[str] = []
    parts.append(f"✨ <b>Your {stats.year} Fitness Wrapped</b> ✨")
    parts.append(_headline(stats.total_classes))

    parts.append(
        f"\n🏋️ You attended <b>{stats.total_classes}</b> "
        f"{'class' if stats.total_classes == 1 else 'classes'} this year"
        f" — about <b>{stats.total_hours:g}h</b> of training!"
    )

    delta_line = _format_delta(stats)
    if delta_line:
        parts.append(delta_line)

    if stats.longest_streak_weeks >= 2:
        parts.append(
            f"🔥 Longest streak: <b>{stats.longest_streak_weeks} weeks</b> in a row!"
        )

    if stats.top_classes:
        parts.append("\n" + _format_ranking("Top Classes 🤸", stats.top_classes, "time"))

    if stats.top_trainers:
        parts.append("\n" + _format_ranking("Top Trainers 👤", stats.top_trainers, "class"))

    if stats.top_months:
        parts.append("\n" + _format_ranking("Most Productive Months 📅", stats.top_months, "class"))

    if stats.favorite_weekday:
        day, count = stats.favorite_weekday
        parts.append(
            f"\n📆 Your go-to day was <b>{day}</b> "
            f"({count} {'class' if count == 1 else 'classes'})."
        )

    if stats.personality:
        parts.append(f"🕒 Your workout personality: <b>{stats.personality}</b>")

    parts.append("\n🎉 Here's to an even stronger next year. See you in the gym! 💪")
    return "\n".join(parts)
