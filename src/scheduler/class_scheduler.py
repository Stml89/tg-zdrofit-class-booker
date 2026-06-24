"""Scheduler for automatic class checking with concurrent user processing."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, List, Dict, Tuple
import asyncio
import time

from src.database.db import Database
from src.api.zdrofit_client import ZdrofitAPIClient
from src.telegram_bot.notifications import NotificationSender
from src.milestones import get_new_milestones
from src.reminders import find_reminder_filter, parse_reminder_time, should_send_reminder
from src.utils.logger import get_logger
from config.config import MAX_CONCURRENT_USERS, SCHEDULER_TIMEOUT, REMINDER_CHECK_INTERVAL_MINUTES

logger = get_logger(__name__)
db = Database()


class ClassCheckScheduler:
    """Scheduler for periodic class availability checks with concurrent processing."""
    
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
            # Frequent job to deliver upcoming-training reminders on time
            self.scheduler.add_job(
                self._check_reminders_job,
                CronTrigger(minute=f"*/{REMINDER_CHECK_INTERVAL_MINUTES}"),
                id='check_reminders',
                name='Check training reminders',
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
                future.result(timeout=SCHEDULER_TIMEOUT)
            else:
                # Fallback: create a new event loop
                asyncio.run(self._async_check_classes())
            logger.info("Periodic class check completed successfully", extra={'user_id': 'system'})
        except Exception as e:
            logger.error(f"Periodic class check failed: {e}", extra={'user_id': 'system'})
        finally:
            logger.info("=" * 50)
    
    async def _async_check_classes(self):
        """Async function to check classes for all users concurrently."""
        # Check for expired pauses and notify users
        await self._check_expired_pauses()
        
        users = db.get_all_users()
        logger.info(f"Found {len(users)} users to check", extra={'user_id': 'system'})
        
        if not users:
            logger.warning("No users registered in the system", extra={'user_id': 'system'})
            return
        
        # Process users concurrently with a semaphore to limit parallelism
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_USERS)
        start_time = time.monotonic()
        
        async def check_user_with_limit(user):
            async with semaphore:
                try:
                    await self._check_user_classes(user.telegram_id, user.zdrofit_email, user.zdrofit_password)
                except Exception as e:
                    logger.error(f"Error checking classes for user: {e}", extra={'user_id': user.telegram_id})
        
        # Run all users concurrently (semaphore limits actual parallelism)
        await asyncio.gather(*[check_user_with_limit(user) for user in users])
        
        elapsed = time.monotonic() - start_time
        logger.info(f"All {len(users)} users processed in {elapsed:.1f}s (max_concurrent={MAX_CONCURRENT_USERS})", 
                    extra={'user_id': 'system'})
    
    def _check_reminders_job(self):
        """Job that runs frequently to deliver upcoming-training reminders."""
        try:
            if self.loop and not self.loop.is_closed():
                future = asyncio.run_coroutine_threadsafe(
                    self._async_check_reminders(),
                    self.loop
                )
                future.result(timeout=SCHEDULER_TIMEOUT)
            else:
                asyncio.run(self._async_check_reminders())
        except Exception as e:
            logger.error(f"Reminder check failed: {e}", extra={'user_id': 'system'})
    
    async def _async_check_reminders(self):
        """Async function to check training reminders for all users concurrently."""
        users = db.get_all_users()
        if not users:
            return
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_USERS)
        
        async def check_user_with_limit(user):
            async with semaphore:
                try:
                    await self._check_user_reminders(user.telegram_id, user.zdrofit_email, user.zdrofit_password)
                except Exception as e:
                    logger.error(f"Error checking reminders for user: {e}", extra={'user_id': user.telegram_id})
        
        await asyncio.gather(*[check_user_with_limit(user) for user in users])
    
    # ==================== Blocking API helpers (run in thread pool) ====================
    
    @staticmethod
    def _sync_authenticate(client: ZdrofitAPIClient, user_id: int) -> bool:
        """Authenticate with Zdrofit API (blocking, runs in thread)."""
        return client.authenticate(user_id)
    
    @staticmethod
    def _sync_get_classes(client: ZdrofitAPIClient, user_filter, user_id: int) -> List[Dict]:
        """Get classes by filter (blocking, runs in thread)."""
        return client.get_classes_by_filter(user_filter, user_id)
    
    @staticmethod
    def _sync_get_default_classes(client: ZdrofitAPIClient, user_id: int, club_id: int) -> List[Dict]:
        """Get default club classes (blocking, runs in thread)."""
        return client.get_available_classes(user_id, club_id=club_id)
    
    @staticmethod
    def _sync_book_class(client: ZdrofitAPIClient, class_id: str, user_id: int) -> bool:
        """Book a class (blocking, runs in thread)."""
        return client.book_class(class_id, user_id)
    
    # ==================== Main user processing ====================
    
    async def _check_user_classes(self, user_id: int, email: str, password: str):
        """Check available classes for a specific user (non-blocking)."""
        try:
            logger.info(f"Starting class check", extra={'user_id': user_id})
            
            # Authenticate with zdrofit (offload blocking call to thread)
            client = ZdrofitAPIClient(email, password)
            authenticated = await asyncio.to_thread(self._sync_authenticate, client, user_id)
            if not authenticated:
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
            
            # Get available classes for each filter (offload blocking calls to threads)
            if user_filters:
                active_filters = [f for f in user_filters if not f.is_paused and f.club_id]
                
                # Log skipped paused filters
                for user_filter in user_filters:
                    if user_filter.is_paused:
                        logger.debug(f"Filter {user_filter.id} is paused until {user_filter.paused_until}, skipping", 
                                    extra={'user_id': user_id})
                
                # Fetch classes for all active filters concurrently in threads
                if active_filters:
                    fetch_tasks = [
                        asyncio.to_thread(self._sync_get_classes, client, user_filter, user_id)
                        for user_filter in active_filters
                    ]
                    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                    
                    for user_filter, result in zip(active_filters, results):
                        if isinstance(result, Exception):
                            logger.error(f"Error fetching classes for filter {user_filter.id}: {result}", 
                                        extra={'user_id': user_id})
                            continue
                        classes = result
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
                # No filters - get default club classes (offload to thread)
                classes = await asyncio.to_thread(self._sync_get_default_classes, client, user_id, 7)
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
            
            # Get classes the user marked as "Not Interested" (skipped)
            skipped_class_ids = set(db.get_skipped_class_ids(user_id))
            logger.debug(f"User has {len(skipped_class_ids)} skipped classes", extra={'user_id': user_id})
            
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
                        # Attempt to auto-book (offload booking to thread)
                        logger.info(f"Attempting to auto-book class {class_id} for filter {user_filter.id}", 
                                    extra={'user_id': user_id})
                        try:
                            booked = await asyncio.to_thread(self._sync_book_class, client, class_id, user_id)
                            if booked:
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

                # If not auto-booked, send notification for manual booking
                if not auto_booked:
                    # Skip classes the user marked as "Not Interested"
                    if class_id in skipped_class_ids:
                        logger.debug(f"Class {class_id} was skipped by user, not notifying", extra={'user_id': user_id})
                        continue
                    
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
            
            # Check milestones based on past attended classes
            await self._check_milestones(user_id, client)
            
        except Exception as e:
            logger.error(f"Error during class check: {str(e)}", extra={'user_id': user_id})

    async def _check_user_reminders(self, user_id: int, email: str, password: str):
        """Send reminders for the user's upcoming booked trainings (per-filter setting)."""
        # Only do work if the user has at least one active filter with reminders enabled
        filters = db.get_all_filters(user_id)
        reminder_filters = [f for f in filters if f.reminder_minutes and not f.is_paused]
        if not reminder_filters:
            return
        
        from datetime import datetime
        
        # Authenticate and fetch the user's schedule (upcoming booked classes)
        client = ZdrofitAPIClient(email, password)
        authenticated = await asyncio.to_thread(self._sync_authenticate, client, user_id)
        if not authenticated:
            logger.warning(f"Reminder check: failed to authenticate", extra={'user_id': user_id})
            return
        
        schedule = await asyncio.to_thread(client.get_user_schedule, user_id)
        if not schedule:
            return
        
        now = datetime.now()
        for class_item in schedule:
            class_id = class_item.get("class_id")
            if not class_id:
                continue
            
            matched = find_reminder_filter(class_item, reminder_filters)
            if not matched:
                continue
            
            start_time = parse_reminder_time(class_item.get("start_time"))
            if not should_send_reminder(start_time, matched.reminder_minutes, now):
                continue
            
            # Avoid sending the same reminder more than once
            if db.is_reminder_sent(user_id, str(class_id)):
                continue
            
            await self.notification_sender.send_training_reminder(
                user_id, class_item, matched.reminder_minutes
            )
            db.add_sent_reminder(user_id, str(class_id), matched.reminder_minutes)
            logger.info(f"Training reminder sent for class {class_id}", extra={'user_id': user_id})

    async def _check_milestones(self, user_id: int, client: ZdrofitAPIClient):
        """Check if user has reached any new milestones based on attended classes."""
        try:
            # Get user's past classes count from API
            schedule = await asyncio.to_thread(client.get_user_schedule, user_id)
            from datetime import datetime
            now = datetime.now()
            attended_count = 0
            for cls in schedule:
                start_time_str = cls.get("start_time", "")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        if start_time < now:
                            attended_count += 1
                    except (ValueError, TypeError):
                        pass

            if attended_count == 0:
                return

            # Get already awarded milestones
            awarded = db.get_user_milestones(user_id)
            new_milestones = get_new_milestones(attended_count, awarded)

            for milestone in new_milestones:
                if milestone.type == "badge" and milestone.badge_path:
                    await self.notification_sender.send_milestone_badge(
                        user_id, milestone.text, str(milestone.badge_path)
                    )
                else:
                    await self.notification_sender.send_milestone_message(user_id, milestone.text)
                db.add_user_milestone(user_id, milestone.count)
                logger.info(f"Milestone {milestone.count} awarded", extra={'user_id': user_id})

        except Exception as e:
            logger.error(f"Error checking milestones: {e}", extra={'user_id': user_id})

    async def _check_expired_pauses(self):
        """Check for expired pauses and notify users, then clear the pause."""
        try:
            expired_filters = db.get_expired_paused_filters()
            for user_filter in expired_filters:
                # Clear the pause
                db.unpause_filter(user_filter.id, user_filter.user_id)
                logger.info(f"Filter {user_filter.id} pause expired, reactivating", 
                           extra={'user_id': user_filter.user_id})
                
                # Notify user
                if self.notification_sender:
                    try:
                        await self.notification_sender.send_filter_unpaused_notification(
                            user_filter.user_id, user_filter
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send unpause notification: {e}", 
                                     extra={'user_id': user_filter.user_id})
        except Exception as e:
            logger.error(f"Error checking expired pauses: {e}", extra={'user_id': 'system'})


# Global scheduler instance
scheduler = ClassCheckScheduler()
