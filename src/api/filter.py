"""Filtering logic for classes."""

from typing import List, Dict, Optional
from datetime import datetime
from src.database.models import UserFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)


def filter_classes(classes: List[Dict], user_filter: Optional[UserFilter], user_id: int = None) -> List[Dict]:
    """
    Filter available classes based on user preferences.
    
    Args:
        classes: List of available classes from API
        user_filter: User's filter preferences
        user_id: Telegram user ID for logging
    
    Returns:
        Filtered list of classes
    """
    if not user_filter:
        logger.info(f"No filters set, returning all classes", extra={'user_id': user_id})
        return classes
    
    filtered = classes
    
    # Filter by zone/gym
    if user_filter.zone_id:
        filtered = [c for c in filtered if c.get("ZoneId") == user_filter.zone_id or c.get("zone_id") == user_filter.zone_id]
        logger.debug(f"Filtered by zone: {user_filter.zone_id}, remaining: {len(filtered)}", extra={'user_id': user_id})
    
    # Filter by trainer
    if user_filter.trainer_id:
        filtered = [c for c in filtered if c.get("TrainerId") == user_filter.trainer_id or c.get("trainer_id") == user_filter.trainer_id]
        logger.debug(f"Filtered by trainer: {user_filter.trainer_id}, remaining: {len(filtered)}", extra={'user_id': user_id})
    
    # Filter by timetable/activity type
    if user_filter.timetable_id:
        filtered = [c for c in filtered if c.get("TimetableId") == user_filter.timetable_id or c.get("timetable_id") == user_filter.timetable_id]
        logger.debug(f"Filtered by timetable: {user_filter.timetable_id}, remaining: {len(filtered)}", extra={'user_id': user_id})
    
    # Filter only classes with available spots
    filtered = [c for c in filtered if c.get("AvailableSpots", c.get("available_spots", 0)) > 0]
    
    logger.info(f"Filtering complete: {len(filtered)} classes match criteria", extra={'user_id': user_id})
    return filtered

def format_class_for_telegram(class_data: Dict, user_id: int = None) -> str:
    """
    Format class data for Telegram message.
    
    Args:
        class_data: Class data from API
        user_id: Telegram user ID for logging
    
    Returns:
        Formatted message string
    """
    try:
        title = class_data.get("title", "Unknown")
        gym_name = class_data.get("gym_name", "Unknown")
        trainer_name = class_data.get("trainer_name", "Unknown")
        activity_type = class_data.get("activity_type", "Unknown")
        start_time = class_data.get("start_time", "Unknown")
        end_time = class_data.get("end_time", "Unknown")
        available_spots = class_data.get("available_spots", 0)
        
        # Parse datetime if it's a string
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                start_time = start_time.strftime("%d.%m.%Y %H:%M")
            except:
                pass
        
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                end_time = end_time.strftime("%H:%M")
            except:
                pass
        
        message = (
            f"<b>{title}</b>\n"
            f"📍 Зал: {gym_name}\n"
            f"Тренер: {trainer_name}\n"
            f"Тип: {activity_type}\n"
            f"Время: {start_time} - {end_time}\n"
            f"💪 Свободных мест: {available_spots}"
        )
        
        return message
    except Exception as e:
        logger.error(f"Error formatting class: {e}", extra={'user_id': user_id})
        return str(class_data)
