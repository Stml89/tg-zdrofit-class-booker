"""Utility functions and helpers."""

from datetime import datetime, timedelta
from typing import Optional


def parse_datetime(date_string: str) -> Optional[datetime]:
    """
    Parse ISO format datetime string.
    
    Args:
        date_string: ISO format datetime string
    
    Returns:
        datetime object or None
    """
    try:
        # Handle Z timezone indicator
        date_string = date_string.replace('Z', '+00:00')
        return datetime.fromisoformat(date_string)
    except (ValueError, AttributeError):
        return None


def format_datetime_display(dt: datetime) -> str:
    """
    Format datetime for display in messages.
    
    Args:
        dt: datetime object
    
    Returns:
        Formatted string like "01.01.2026 14:30"
    """
    if not dt:
        return "Unknown"
    try:
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return str(dt)


def is_class_available_soon(start_time: datetime) -> bool:
    """
    Check if class is available for booking (within 48 hours).
    
    Args:
        start_time: Class start time
    
    Returns:
        True if class is within 48 hours
    """
    if not start_time:
        return False
    
    now = datetime.now()
    time_until_class = start_time - now
    
    return timedelta(0) < time_until_class <= timedelta(hours=48)

