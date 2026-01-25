"""Scheduler for automatic class checking."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
import asyncio

from src.database.db import Database
from src.api.zdrofit_client import ZdrofitAPIClient
from src.telegram_bot.notifications import NotificationSender
from src.utils.logger import get_logger

logger = get_logger(__name__)
db = Database()


class ClassCheckScheduler:
    """Scheduler for periodic class availability checks."""
    
    def __init__(self, app=None, loop=None):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.app = app
        self.notification_sender = None
        self.loop = loop  # Event loop reference
    
    def start(self):
        """Start the scheduler to run at the beginning of every hour (HH:00)."""
        if not self.is_running:
            # Initialize notification sender with bot from app if available
            if self.app:
                self.notification_sender = NotificationSender(self.app.bot)
            else:
                self.notification_sender = NotificationSender()
            
            self.scheduler.add_job(
                self._check_classes_job,
                CronTrigger(minute="0"), 
                id='check_classes',
                name='Check available classes',
                replace_existing=True
            )
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler started, checking at the beginning of every hour (HH:00)", extra={'user_id': 'system'})
    
    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
    
    def _check_classes_job(self):
        """Job that runs periodically to check for available classes."""
        logger.info("=" * 50)
        logger.info("Starting periodic class check", extra={'user_id': 'system'})
        
        try:
            # If we have an event loop, use it; otherwise create a new one
            if self.loop and not self.loop.is_closed():
                # Schedule the async task on the existing event loop
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(
                    self._async_check_classes(),
                    self.loop
                )
                # Wait for the result (with timeout)
                future.result(timeout=300)  # 5 minute timeout
            else:
                # Fallback: create a new event loop
                asyncio.run(self._async_check_classes())
            logger.info("Periodic class check completed successfully", extra={'user_id': 'system'})
        except Exception as e:
            logger.error(f"Periodic class check failed: {e}", extra={'user_id': 'system'})
        finally:
            logger.info("=" * 50)
    
    async def _async_check_classes(self):
        """Async function to check classes for all users."""
        users = db.get_all_users()
        logger.info(f"Found {len(users)} users to check", extra={'user_id': 'system'})
        
        if not users:
            logger.warning("No users registered in the system", extra={'user_id': 'system'})
            return
        
        for user in users:
            try:
                await self._check_user_classes(user.telegram_id, user.zdrofit_email, user.zdrofit_password)
            except Exception as e:
                logger.error(f"Error checking classes for user: {e}", extra={'user_id': user.telegram_id})
    
    async def _check_user_classes(self, user_id: int, email: str, password: str):
        """Check available classes for a specific user."""
        try:
            logger.info(f"Starting class check", extra={'user_id': user_id})
            
            # Authenticate with zdrofit
            client = ZdrofitAPIClient(email, password)
            if not client.authenticate(user_id):
                logger.error(f"Failed to authenticate with zdrofit", extra={'user_id': user_id})
                await self.notification_sender.send_error_notification(
                    user_id, 
                    "Authentication error. Please check your credentials."
                )
                return
            
            logger.debug(f"Successfully authenticated with zdrofit", extra={'user_id': user_id})
            
            # Get all user filters to apply
            user_filters = db.get_all_filters(user_id)
            logger.debug(f"User has {len(user_filters)} filters", extra={'user_id': user_id})
            
            # Map class_id to the filters it matches (to track which filter it came from)
            class_to_filters = {}  # {class_id: [filter1, filter2, ...]}
            all_classes = []
            
            # Get available classes for each filter
            if user_filters:
                for user_filter in user_filters:
                    if user_filter.club_id:
                        classes = client.get_classes_by_filter(user_filter, user_id)
                        all_classes.extend(classes)
                        # Track which filters match this class
                        for cls in classes:
                            class_id = cls.get("id")
                            if class_id not in class_to_filters:
                                class_to_filters[class_id] = []
                            class_to_filters[class_id].append(user_filter)
                        logger.info(f"Retrieved {len(classes)} classes for filter: {user_filter.club_name}", 
                                   extra={'user_id': user_id})
            else:
                # No filters - get default club classes
                classes = client.get_available_classes(user_id, club_id=7)
                all_classes = classes
                logger.info(f"Retrieved {len(classes)} available classes (no filters)", extra={'user_id': user_id})
            
            # Remove duplicates by class ID (in case multiple filters overlap)
            seen_ids = set()
            classes = []
            for c in all_classes:
                class_id = c.get("id")
                if class_id not in seen_ids:
                    seen_ids.add(class_id)
                    classes.append(c)
            
            # Get already booked classes
            booked_classes = db.get_user_bookings(user_id)
            booked_class_ids = {b.class_id for b in booked_classes}
            logger.debug(f"User has {len(booked_class_ids)} booked classes", extra={'user_id': user_id})
            
            if not classes:
                logger.info(f"No available classes found", extra={'user_id': user_id})
                return
            
            # Process classes: auto-book or notify
            notifications_sent = 0
            auto_bookings_made = 0
            
            for class_data in classes:
                class_id = class_data.get("id")
                
                # Check if already booked
                if class_id in booked_class_ids:
                    logger.debug(f"Class {class_id} already booked, skipping", extra={'user_id': user_id})
                    continue
                
                # Get matching filters for this class
                matching_filters = class_to_filters.get(class_id, [])
                
                # Try to auto-book with matching filters that have auto_booking enabled
                auto_booked = False
                for user_filter in matching_filters:
                    if user_filter.auto_booking:
                        # Check booking count for this filter
                        booking_count = db.count_filter_bookings(user_id, user_filter.id)
                        if booking_count < 3:
                            # Attempt to auto-book
                            logger.info(f"Attempting to auto-book class {class_id} for filter {user_filter.id}", 
                                       extra={'user_id': user_id})
                            try:
                                # Attempt booking through API
                                if client.book_class(class_id, user_id):
                                    # Save booking to database with auto_booking flag
                                    from src.database.models import Booking
                                    booking = Booking(
                                        user_id=user_id,
                                        class_id=class_id,
                                        title=class_data.get("title"),
                                        start_time=class_data.get("start_time"),
                                        filter_id=user_filter.id,
                                        is_auto_booked=True
                                    )
                                    db.add_booking(booking)
                                    auto_bookings_made += 1
                                    auto_booked = True
                                    logger.info(f"Successfully auto-booked class {class_id}", extra={'user_id': user_id})
                                    # Send confirmation notification
                                    await self.notification_sender.send_auto_booking_confirmation(
                                        user_id, class_data, user_filter
                                    )
                                    break  # Don't try other filters since we already booked
                                else:
                                    logger.warning(f"API booking failed for class {class_id}", extra={'user_id': user_id})
                            except Exception as e:
                                logger.warning(f"Error auto-booking class {class_id}: {e}", extra={'user_id': user_id})
                        else:
                            logger.info(f"Filter {user_filter.id} already has {booking_count} bookings (max 3), " + 
                                       f"won't auto-book class {class_id}", extra={'user_id': user_id})
                
                # If not auto-booked, send notification for manual booking
                if not auto_booked:
                    logger.info(f"Sending notification for class {class_id}: {class_data.get('title')}", 
                               extra={'user_id': user_id})
                    try:
                        await self.notification_sender.send_class_notification(user_id, class_data, class_id)
                        notifications_sent += 1
                        logger.debug(f"Notification successfully sent", extra={'user_id': user_id})
                    except Exception as e:
                        logger.warning(f"Failed to send notification for class {class_id}, will retry later: {e}", 
                                     extra={'user_id': user_id})
                        # Don't mark as notified if sending failed - will retry next time
            
            logger.info(f"Class check completed - {auto_bookings_made} auto-booked, {notifications_sent} notifications sent", 
                       extra={'user_id': user_id})
            
        except Exception as e:
            logger.error(f"Error during class check: {str(e)}", extra={'user_id': user_id})


# Global scheduler instance
scheduler = ClassCheckScheduler()
