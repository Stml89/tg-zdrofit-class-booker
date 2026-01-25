"""Notification sender for class updates."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from typing import List, Dict
from datetime import datetime, timedelta
import re

from src.utils.logger import get_logger
from config.config import (
    TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT,
    TELEGRAM_POOL_TIMEOUT,
    TELEGRAM_POOL_SIZE
)

logger = get_logger(__name__)

DAY_NAMES = {
    0: "Monday",
    1: "Tuesday", 
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}


class NotificationSender:
    """Send notifications to users about available classes."""
    
    def __init__(self, bot: Bot = None):
        """Initialize notification sender with optional Bot instance.
        
        Args:
            bot: Telegram Bot instance. If not provided, creates one with default settings.
        """
        if bot:
            self.bot = bot
        else:
            # Create bot with configured HTTP client (fallback for testing)
            http_client = HTTPXRequest(
                connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
                read_timeout=TELEGRAM_READ_TIMEOUT,
                write_timeout=TELEGRAM_WRITE_TIMEOUT,
                pool_timeout=TELEGRAM_POOL_TIMEOUT,
                connection_pool_size=TELEGRAM_POOL_SIZE
            )
            from config.config import TELEGRAM_BOT_TOKEN
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN, request=http_client)
    
    async def send_class_notification(self, user_id: int, class_data: Dict, class_id: str):
        """
        Send notification about available class.
        
        Args:
            user_id: Telegram user ID
            class_data: Class data from API
            class_id: Unique class ID for callbacks
        """
        try:
            title = class_data.get("title", "Unknown")
            gym_name = class_data.get("gym_name", "Zdrofit")
            trainer_name = class_data.get("trainer_name", "Unknown")
            activity_type = class_data.get("activity_type", "Unknown")
            start_time = class_data.get("start_time", "Unknown")
            duration_str = class_data.get("duration", "")
            available_spots = class_data.get("available_spots", 0)
            
            end_time = "Unknown"
            day_of_week = "Unknown"
            formatted_date = "Unknown"
            
            # Parse start time and calculate end time from duration
            if isinstance(start_time, str):
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    
                    # Get day of week name
                    day_of_week = DAY_NAMES.get(dt.weekday(), "Unknown")
                    
                    # Format date as "Day, DD.MM.YYYY"
                    formatted_date = f"{day_of_week}, {dt.strftime('%d.%m.%Y')}"
                    
                    # Format time as HH:MM
                    start_time_only = dt.strftime("%H:%M")
                    
                    # Parse duration (e.g., "PT55M" or "PT1H30M")
                    if duration_str:
                        # Extract hours and minutes from ISO 8601 duration
                        hours = 0
                        minutes = 0
                        
                        # Match PT pattern
                        if 'H' in duration_str:
                            h_match = re.search(r'(\d+)H', duration_str)
                            if h_match:
                                hours = int(h_match.group(1))
                        
                        if 'M' in duration_str:
                            m_match = re.search(r'(\d+)M', duration_str)
                            if m_match:
                                minutes = int(m_match.group(1))
                        
                        # Calculate end time
                        end_dt = dt + timedelta(hours=hours, minutes=minutes)
                        end_time = end_dt.strftime("%H:%M")
                    
                    start_time = start_time_only
                except Exception as e:
                    logger.warning(f"Error parsing start time: {e}", extra={'user_id': user_id})
                    start_time = "Unknown"
                    end_time = "Unknown"
                    formatted_date = "Unknown"
            
            message = (
                f"<b>Free spot found for a class!</b>\n\n"
                f"<b>{title}</b>\n"
                f"Gym: {gym_name}\n"
                f"Trainer: {trainer_name}\n"
                f"Type: {activity_type}\n"
                f"Day: {formatted_date}\n"
                f"Time: {start_time} - {end_time}\n"
                f"Available spots: {available_spots}"
            )
            
            # Booking buttons
            keyboard = [
                [
                    InlineKeyboardButton("Book", callback_data=f"book_{class_id}"),
                    InlineKeyboardButton("Not Interested", callback_data=f"skip_{class_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
            logger.info(f"Notification sent for class {class_id}", extra={'user_id': user_id})
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}", extra={'user_id': user_id})
            # Re-raise exception so scheduler knows notification failed
            raise
    
    async def send_booking_confirmation(self, user_id: int, class_data: Dict):
        """Send booking confirmation message."""
        try:
            title = class_data.get("title", "Unknown")
            start_time = class_data.get("start_time", "Unknown")
            
            if isinstance(start_time, str):
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            
            message = (
                f"<b>Class booked!</b>\n\n"
                f"{title}\n"
                f"{start_time}"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Booking confirmation sent", extra={'user_id': user_id})
            
        except Exception as e:
            logger.error(f"Error sending booking confirmation: {e}", extra={'user_id': user_id})
    
    async def send_auto_booking_confirmation(self, user_id: int, class_data: Dict, user_filter):
        """Send automatic booking confirmation notification."""
        try:
            title = class_data.get("title", "Unknown")
            start_time = class_data.get("start_time", "Unknown")
            gym_name = class_data.get("gym_name", "Zdrofit")
            trainer_name = class_data.get("trainer_name", "Unknown")
            
            if isinstance(start_time, str):
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            
            message = (
                f"🤖 <b>Auto-booking successful!</b>\n\n"
                f"<b>{title}</b>\n"
                f"Gym: {gym_name}\n"
                f"Trainer: {trainer_name}\n"
                f"Date & Time: {start_time}\n\n"
                f"<i>Filter: {user_filter.club_name} - {user_filter.timetable_name}</i>"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Auto-booking confirmation sent", extra={'user_id': user_id})
            
        except Exception as e:
            logger.error(f"Error sending auto-booking confirmation: {e}", extra={'user_id': user_id})
    
    async def send_error_notification(self, user_id: int, error_message: str):
        """Send error notification."""
        try:
            message = f"<b>Error:</b> {error_message}"
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            logger.warning(f"Error notification sent: {error_message}", extra={'user_id': user_id})
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}", extra={'user_id': user_id})
