"""Milestone definitions and logic for user achievements."""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "badges"


@dataclass
class Milestone:
    """A milestone achievement definition."""
    count: int
    type: str  # "message" or "badge"
    text: str
    badge_filename: Optional[str] = None

    @property
    def badge_path(self) -> Optional[Path]:
        if self.badge_filename:
            return ASSETS_DIR / self.badge_filename
        return None


# Fixed milestones (up to 200)
FIXED_MILESTONES: List[Milestone] = [
    Milestone(
        count=5,
        type="message",
        text="🎉 <b>5 classes completed!</b>\n\nGreat start! Consistency is the key to results. Keep showing up!",
    ),
    Milestone(
        count=10,
        type="badge",
        text="🏅 <b>10 classes — First Milestone!</b>\n\nYou've hit double digits! Here's your first badge:",
        badge_filename="badge_010.png",
    ),
    Milestone(
        count=15,
        type="message",
        text="💪 <b>15 classes done!</b>\n\nYou're building a habit that will change your life. The hardest part is over!",
    ),
    Milestone(
        count=20,
        type="badge",
        text="🛡️ <b>20 classes — Dedicated!</b>\n\nYou've earned the Dedicated badge. Your commitment is showing!",
        badge_filename="badge_020.png",
    ),
    Milestone(
        count=25,
        type="message",
        text="🔥 <b>25 classes!</b>\n\nQuarter century of workouts! You're officially in the top league of consistency.",
    ),
    Milestone(
        count=30,
        type="badge",
        text="⚔️ <b>30 classes — Warrior!</b>\n\nNothing stops a warrior. You've proven your dedication:",
        badge_filename="badge_030.png",
    ),
    Milestone(
        count=35,
        type="message",
        text="🚀 <b>35 classes!</b>\n\nFitness isn't what you do anymore — it's who you are. Incredible progress!",
    ),
    Milestone(
        count=40,
        type="badge",
        text="🏋️ <b>40 classes — Iron Will!</b>\n\nForged in sweat and determination. You've earned this:",
        badge_filename="badge_040.png",
    ),
    Milestone(
        count=50,
        type="badge",
        text="🏆 <b>50 classes — Half Century Hero!</b>\n\n50 classes is a massive achievement. Wear this badge with pride:",
        badge_filename="badge_050.png",
    ),
    Milestone(
        count=100,
        type="badge",
        text="⚔️ <b>100 classes — Centurion!</b>\n\nA hundred classes. You are an absolute legend:",
        badge_filename="badge_100.png",
    ),
    Milestone(
        count=150,
        type="badge",
        text="👑 <b>150 classes — Legend!</b>\n\nLegendary status achieved. Very few reach this level:",
        badge_filename="badge_150.png",
    ),
    Milestone(
        count=200,
        type="badge",
        text="🌟 <b>200 classes — Unstoppable!</b>\n\nTwo hundred classes. You are truly unstoppable:",
        badge_filename="badge_200.png",
    ),
]

# Dynamic motivation messages for milestones > 200 (every 50, not multiple of 100)
DYNAMIC_MESSAGES = [
    "🚀 <b>{count} classes!</b>\n\nYou're a fitness machine. Most people only dream about your consistency!",
    "⭐ <b>{count} classes!</b>\n\nEvery class makes you stronger. You're proof that dedication pays off!",
    "🔥 <b>{count} classes!</b>\n\nThe gym is your second home. Your discipline is extraordinary!",
    "💎 <b>{count} classes!</b>\n\nDiamond-level commitment. You inspire everyone around you!",
    "🌊 <b>{count} classes!</b>\n\nUnstoppable like a wave. Nothing can break your streak!",
]

# Dynamic badge text for milestones > 200 (every 100)
DYNAMIC_BADGE_TEXT = "🏆 <b>{count} classes — Titan!</b>\n\nAnother hundred conquered. Here's your badge:"


def get_milestone(count: int) -> Optional[Milestone]:
    """Get milestone for a specific class count, or None if not a milestone."""
    # Check fixed milestones first
    for milestone in FIXED_MILESTONES:
        if milestone.count == count:
            return milestone

    # Dynamic milestones (above 200)
    if count > 200 and count % 100 == 0:
        # Badge every 100
        return Milestone(
            count=count,
            type="badge",
            text=DYNAMIC_BADGE_TEXT.format(count=count),
            badge_filename=f"badge_dynamic.png",
        )
    elif count > 200 and count % 50 == 0:
        # Message every 50 (that's not a multiple of 100)
        msg_idx = ((count // 50) - 1) % len(DYNAMIC_MESSAGES)
        return Milestone(
            count=count,
            type="message",
            text=DYNAMIC_MESSAGES[msg_idx].format(count=count),
        )

    return None


def get_new_milestones(attended_count: int, already_awarded: List[int]) -> List[Milestone]:
    """Get all milestones reached but not yet awarded.
    
    Args:
        attended_count: Total number of attended classes.
        already_awarded: List of milestone counts already awarded.
        
    Returns:
        List of new milestones to award (sorted by count).
    """
    awarded_set = set(already_awarded)
    new_milestones = []

    # Check all possible milestone counts up to attended_count
    # Fixed milestones
    for milestone in FIXED_MILESTONES:
        if milestone.count <= attended_count and milestone.count not in awarded_set:
            new_milestones.append(milestone)

    # Dynamic milestones (above 200, every 50)
    if attended_count > 200:
        start = 250
        while start <= attended_count:
            if start not in awarded_set:
                milestone = get_milestone(start)
                if milestone:
                    new_milestones.append(milestone)
            start += 50

    new_milestones.sort(key=lambda m: m.count)
    return new_milestones
