"""Telegram bot handlers."""

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime

from src.database.db import Database
from src.database.models import User, UserFilter, Booking
from src.api.zdrofit_client import ZdrofitAPIClient
from src.year_wrap import compute_year_wrap, format_year_wrap_message
from src.utils.logger import get_logger
from config.config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_IDS

logger = get_logger(__name__)
db = Database()


async def show_filter_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show filter confirmation screen."""
    query = update.callback_query
    
    club_name = context.user_data.get('filter_club_name', 'Unknown')
    timetable_name = context.user_data.get('filter_timetable_name', 'Unknown')
    trainer_name = context.user_data.get('filter_trainer_name')
    time_from = context.user_data.get('filter_time_from')
    time_to = context.user_data.get('filter_time_to')
    time_hours = context.user_data.get('filter_time_hours')
    weekdays = context.user_data.get('filter_weekdays')
    
    message = (
        "<b>Your filters:</b>\n\n"
        f"Club: {club_name}\n"
        f"Class: {timetable_name}\n"
    )
    
    if trainer_name:
        message += f"Trainer: {trainer_name}\n"
    
    # Display selected time hours or time range
    if time_hours:
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        message += f"Time: {time_display}\n"
    elif time_from or time_to:
        message += f"Time: {time_from or '00:00'} - {time_to or '23:59'}\n"
    
    if weekdays:
        days_map = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
        selected_days = [days_map.get(int(d)) for d in weekdays.split(',')]
        message += f"Days: {', '.join(selected_days)}\n"
    
    keyboard = [
        [InlineKeyboardButton("✓ Save", callback_data="filter_confirm")],
        [InlineKeyboardButton("Back", callback_data="filter_back")],
        [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, query):
    """Show time interval selection screen."""
    selected = set()
    if context.user_data.get('filter_times'):
        selected = set(context.user_data.get('filter_times', '').split(','))
    
    keyboard = []
    
    # 18 intervals: 06:00-22:00 in 3 rows of 6
    hours = list(range(6, 23))  # 6 to 22
    
    for row in range(3):
        row_buttons = []
        for col in range(6):
            idx = row * 6 + col
            if idx < len(hours):
                hour = hours[idx]
                hour_str_formatted = f"{hour:02d}"
                is_selected = hour_str_formatted in selected
                button_text = f"{'🔵 ' if is_selected else ''}{hour:02d}:00"
                row_buttons.append(
                    InlineKeyboardButton(button_text, callback_data=f"filter_time_{hour_str_formatted}")
                )
        if row_buttons:
            keyboard.append(row_buttons)
    
    keyboard.append([InlineKeyboardButton("Continue", callback_data="filter_after_time")])
    keyboard.append([InlineKeyboardButton("Skip time filter", callback_data="filter_skip_time")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Select time intervals (optional - select multiple or skip for any time):\n\n🔵 = selected",
        reply_markup=reply_markup
    )


async def show_reminder_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, query):
    """Show training reminder selection screen (default OFF)."""
    context.user_data['filter_step'] = 'reminder'
    
    keyboard = [
        [InlineKeyboardButton("🔕 Off (default)", callback_data="filter_reminder_off")],
        [InlineKeyboardButton("⏰ 15 min before", callback_data="filter_reminder_15")],
        [InlineKeyboardButton("⏰ 30 min before", callback_data="filter_reminder_30")],
        [InlineKeyboardButton("⏰ 60 min before", callback_data="filter_reminder_60")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Enable a training reminder for this filter?\n\n"
        "The bot will remind you about upcoming booked trainings",
        reply_markup=reply_markup
    )


async def save_filter_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, query):
    """Save filter to database with auto_booking setting."""
    try:
        club_id = context.user_data.get('filter_club_id')
        club_name = context.user_data.get('filter_club_name')
        timetable_id = context.user_data.get('filter_timetable_id')
        timetable_name = context.user_data.get('filter_timetable_name')
        trainer_id = context.user_data.get('filter_trainer_id')
        trainer_name = context.user_data.get('filter_trainer_name')
        time_from = context.user_data.get('filter_time_from')
        time_to = context.user_data.get('filter_time_to')
        time_hours = context.user_data.get('filter_time_hours')
        weekdays = context.user_data.get('filter_weekdays')
        auto_booking = context.user_data.get('filter_auto_booking', False)
        reminder_minutes = context.user_data.get('filter_reminder_minutes')
        
        user_filter = UserFilter(
            user_id=user_id,
            club_id=club_id,
            club_name=club_name,
            timetable_id=timetable_id,
            timetable_name=timetable_name,
            trainer_id=trainer_id,
            trainer_name=trainer_name,
            time_from=time_from,
            time_to=time_to,
            weekdays=weekdays,
            auto_booking=auto_booking,
            reminder_minutes=reminder_minutes
        )
        
        if db.add_filter(user_filter):
            context.user_data['filter_mode'] = False
            logger.info(f"Filters saved successfully with auto_booking={auto_booking}, reminder={reminder_minutes}", extra={'user_id': user_id})
            
            weekdays_str = ""
            if weekdays:
                days_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
                selected_days = [days_map.get(int(d)) for d in weekdays.split(',')]
                weekdays_str = f"\nDays: {', '.join(selected_days)}"
            
            # Display time info
            time_str = ""
            if time_hours:
                hours = [int(h) for h in time_hours.split(',')]
                time_str = f"\nTime: {', '.join(f'{h:02d}:00' for h in hours)}"
            elif time_from or time_to:
                time_str = f"\nTime: {time_from or '00:00'} - {time_to or '23:59'}"
            
            auto_booking_str = "\n🤖 Auto-booking: ENABLED" if auto_booking else "\n🔔 Auto-booking: Disabled"
            reminder_str = f"\n⏰ Reminder: {reminder_minutes} min before" if reminder_minutes else "\n⏰ Reminder: Off"
            
            await query.edit_message_text(
                f"✓ Filters saved!\n\n"
                f"Club: {club_name}\n"
                f"Class: {timetable_name}\n"
                f"Trainer: {trainer_name or 'Any'}{time_str}{weekdays_str}{auto_booking_str}{reminder_str}\n\n"
                f"Now you can use /bookings to view available classes"
            )
        else:
            await query.edit_message_text("Error saving filters. Please try again.")
    except Exception as e:
        logger.error(f"Error saving filter: {e}", extra={'user_id': user_id})
        await query.edit_message_text("Error saving filters. Please try again.")


class BotHandlers:
    """Telegram bot command handlers."""
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - welcome message."""
        user_id = update.effective_user.id
        user = db.get_user(user_id)
        
        logger.info(f"User started bot", extra={'user_id': user_id})
        
        message = (
            "Welcome to zdrofit Class Booker!\n\n"
            "This bot automatically checks for available class spots and notifies you.\n\n"
            "Available commands:\n"
            "/login - Login your Zdrofit account\n"
            "/filters - Set search filters(limited, uses hardcoded values for now)\n"
            "/bookings - View your active bookings\n"
            "/past_classes - View your last 5 attended classes\n"
            "/wrapped - Your year in review (fitness stats)\n"
            "/logout - Logout from account\n"
        )
        
        if user_id in ADMIN_TELEGRAM_IDS:
            message += "/broadcast - Send message to all users\n"
        
        if user:
            message += f"\nYou are already logged in as {user.zdrofit_email}"
        
        await update.message.reply_text(message)
    
    
    @staticmethod
    def _validate_email(email: str) -> bool:
        """Validate email format - simple validation."""
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) and len(email) <= 254
    
    @staticmethod
    def _validate_password(password: str) -> bool:
        """Validate password - basic length check."""
        # Password must be at least 1 character and max 20
        return 1 <= len(password) <= 20
    
    @staticmethod
    async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Login command - start authentication flow."""
        user_id = update.effective_user.id
        logger.info(f"User initiated login", extra={'user_id': user_id})
        
        # Check if already logged in
        existing_user = db.get_user(user_id)
        if existing_user:
            await update.message.reply_text(
                f"You are already logged in as {existing_user.zdrofit_email}\n"
                "Use /logout to exit or enter new credentials to replace."
            )
        
        context.user_data['login_step'] = 'email'
        await update.message.reply_text(
            "Enter your Zdrofit account email:"
        )
    
    @staticmethod
    async def handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle email input during login with validation."""
        user_id = update.effective_user.id
        
        if context.user_data.get('login_step') != 'email':
            return
        
        email = update.message.text.strip()
        
        # Validate email format
        if not BotHandlers._validate_email(email):
            logger.warning(f"Invalid email format provided", extra={'user_id': user_id})
            await update.message.reply_text(
                "❌ Invalid email format. Please enter a valid email address:"
            )
            return
        
        context.user_data['zdrofit_email'] = email
        context.user_data['login_step'] = 'password'
        
        logger.info(f"User provided valid email", extra={'user_id': user_id})
        
        await update.message.reply_text(
            "Enter your Zdrofit account password:"
        )
    
    @staticmethod
    async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle password input during login with validation."""
        user_id = update.effective_user.id
        
        if context.user_data.get('login_step') != 'password':
            return
        
        password = update.message.text
        email = context.user_data.get('zdrofit_email')
        
        # Validate password (basic validation - not empty, reasonable length)
        if not BotHandlers._validate_password(password):
            logger.warning(f"Invalid password provided (length check)", extra={'user_id': user_id})
            await update.message.reply_text(
                "Invalid password. Password must be between 1 and 20 characters.\nPlease try again:"
            )
            return
        
        logger.info(f"User provided password, attempting authentication", extra={'user_id': user_id})
        
        # Try to authenticate
        client = ZdrofitAPIClient(email, password)
        if client.authenticate(user_id):
            # Save user to database
            user = User(telegram_id=user_id, zdrofit_email=email, zdrofit_password=password)
            if db.add_user(user):
                context.user_data.pop('login_step', None)
                context.user_data.pop('zdrofit_email', None)
                
                await update.message.reply_text(
                    f"Login successful!\n"
                    f"Your account: {email}\n\n"
                    "Now set filters /filters to search for classes."
                )
                logger.info(f"User successfully authenticated", extra={'user_id': user_id})
            else:
                await update.message.reply_text("Error saving data. Please try again.")
        else:
            context.user_data.pop('login_step', None)
            context.user_data.pop('zdrofit_email', None)
            await update.message.reply_text(
                "Invalid credentials. Please try again: /login"
            )
    
    @staticmethod
    async def filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Filters command - show menu with options."""
        user_id = update.effective_user.id
        user = db.get_user(user_id)
        
        logger.info(f"User opened filters menu", extra={'user_id': user_id})
        
        if not user:
            await update.message.reply_text(
                "Please login first: /login"
            )
            return
        
        # Show filter menu options
        context.user_data['filter_mode'] = True
        context.user_data['filter_step'] = 'menu'
        
        keyboard = [
            [InlineKeyboardButton("➕ Set Filter", callback_data="filter_menu_set")],
            [InlineKeyboardButton("👁️ View Filter", callback_data="filter_menu_view")],
            [InlineKeyboardButton("⏸️ Pause Filter", callback_data="filter_menu_pause")],
            [InlineKeyboardButton("🗑️ Delete Filter", callback_data="filter_menu_delete")],
            [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Filter Management\n\nSelect an option:",
            reply_markup=reply_markup
        )
    
    @staticmethod
    async def handle_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle filter selection callbacks."""
        user_id = update.effective_user.id
        query = update.callback_query
        
        # Don't answer yet - verify conditions first to avoid timeout
        if not context.user_data.get('filter_mode'):
            try:
                await query.answer()
            except:
                pass
            return
        
        current_step = context.user_data.get('filter_step')
        user = db.get_user(user_id)
        
        if not user:
            try:
                await query.answer()
            except:
                pass
            await query.edit_message_text("Authentication error. Please login again: /login")
            return
        
        # Now answer the query
        try:
            await query.answer()
        except:
            pass  # Ignore if query is already answered or expired
        
        # Menu options (before club selection)
        if query.data == "filter_menu_set":
            # Check filter limit
            user_filters = db.get_all_filters(user_id)
            if len(user_filters) >= 3:
                await query.answer("You already have 3 filters (maximum allowed)", show_alert=True)
                return
            
            # Initialize filter state for setting new filter
            context.user_data['filter_step'] = 'club'
            context.user_data['filter_club_id'] = None
            context.user_data['filter_club_name'] = None
            context.user_data['filter_timetable_id'] = None
            context.user_data['filter_timetable_name'] = None
            context.user_data['filter_category_id'] = None
            context.user_data['filter_trainer_id'] = None
            context.user_data['filter_trainer_name'] = None
            context.user_data['filter_time_from'] = None
            context.user_data['filter_time_to'] = None
            context.user_data['filter_times'] = None  # Store selected hours as "6,7,8,9"
            context.user_data['filter_time_hours'] = None  # Store for display
            context.user_data['filter_weekdays'] = None  # Will store as "1,2,3,4,5" (Mon-Fri)
            context.user_data['filter_auto_booking'] = False  # Enable automatic booking
            context.user_data['filter_reminder_minutes'] = None  # Training reminder lead time (15/30/60 or None=Off)
            
            # Show city selection buttons
            from config.config import AVAILABLE_CLUBS
            keyboard = []
            for city in sorted(AVAILABLE_CLUBS.keys()):
                keyboard.append([
                    InlineKeyboardButton(
                        city,
                        callback_data=f"filter_city_{city}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select a city:",
                reply_markup=reply_markup
            )
            return
        
        elif query.data == "filter_menu_view":
            # View all filters
            user_filters = db.get_all_filters(user_id)
            
            if not user_filters:
                message = "❌ You don't have any filters set yet.\n\nUse 'Set Filter' to create one."
            else:
                message = f"<b>Your Filters ({len(user_filters)}/3):</b>\n\n"
                
                for idx, user_filter in enumerate(user_filters, 1):
                    message += f"<b>Filter {idx}:</b>\n"
                    message += f"  Club: {user_filter.club_name or 'Not set'}\n"
                    message += f"  Class: {user_filter.timetable_name or 'Not set'}\n"
                    
                    if user_filter.trainer_name:
                        message += f"  Trainer: {user_filter.trainer_name}\n"
                    
                    # Display time range
                    if user_filter.time_from or user_filter.time_to:
                        time_display = f"{user_filter.time_from or '00:00'} - {user_filter.time_to or '23:59'}"
                    else:
                        time_display = "Any time"
                    message += f"  Time: {time_display}\n"
                    
                    # Display weekdays if selected
                    if user_filter.weekdays:
                        day_names = {
                            '1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu',
                            '5': 'Fri', '6': 'Sat', '7': 'Sun'
                        }
                        days = [day_names.get(d, d) for d in user_filter.weekdays.split(',')]
                        message += f"  Days: {', '.join(days)}\n"
                    else:
                        message += f"  Days: Any day\n"
                    
                    # Display auto booking status
                    auto_booking_status = "🤖 ENABLED" if user_filter.auto_booking else "🔔 Disabled"
                    message += f"  Auto-booking: {auto_booking_status}\n"
                    
                    # Display reminder status
                    if user_filter.reminder_minutes:
                        message += f"  Reminder: ⏰ {user_filter.reminder_minutes} min before\n"
                    else:
                        message += f"  Reminder: Off\n"
                    
                    # Display pause status
                    if user_filter.is_paused:
                        message += f"  ⏸️ <b>PAUSED</b> until {user_filter.paused_until.strftime('%d.%m.%Y %H:%M')}\n"
                    
                    message += "\n"
            
            keyboard = [
                [InlineKeyboardButton("Back to Menu", callback_data="filter_menu_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        elif query.data == "filter_menu_delete":
            # Show filters to delete
            user_filters = db.get_all_filters(user_id)
            
            if not user_filters:
                message = "❌ You don't have any filters to delete."
                keyboard = [
                    [InlineKeyboardButton("Back to Menu", callback_data="filter_menu_back")],
                    [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
                ]
            else:
                message = "<b>Select filter to delete:</b>\n\n"
                keyboard = []
                
                for idx, user_filter in enumerate(user_filters, 1):
                    filter_desc = f"{idx}. {user_filter.club_name} - {user_filter.timetable_name}"
                    keyboard.append([
                        InlineKeyboardButton(
                            filter_desc,
                            callback_data=f"filter_delete_{user_filter.id}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_menu_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        elif query.data == "filter_menu_pause":
            # Show filters to pause/unpause
            user_filters = db.get_all_filters(user_id)
            
            if not user_filters:
                message = "❌ You don't have any filters to pause."
                keyboard = [
                    [InlineKeyboardButton("Back to Menu", callback_data="filter_menu_back")],
                    [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
                ]
            else:
                message = "<b>Select filter to pause/unpause:</b>\n\n"
                keyboard = []
                
                for idx, user_filter in enumerate(user_filters, 1):
                    if user_filter.is_paused:
                        pause_info = f" ⏸️ paused until {user_filter.paused_until.strftime('%d.%m.%Y %H:%M')}"
                        filter_desc = f"{idx}. {user_filter.club_name} - {user_filter.timetable_name}{pause_info}"
                        keyboard.append([
                            InlineKeyboardButton(
                                f"▶️ Unpause: {user_filter.club_name}",
                                callback_data=f"filter_unpause_{user_filter.id}"
                            )
                        ])
                    else:
                        filter_desc = f"{idx}. {user_filter.club_name} - {user_filter.timetable_name}"
                        keyboard.append([
                            InlineKeyboardButton(
                                f"⏸️ Pause: {filter_desc}",
                                callback_data=f"filter_pause_{user_filter.id}"
                            )
                        ])
                
                keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_menu_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        elif query.data == "filter_menu_back":
            # Go back to main menu
            context.user_data['filter_step'] = 'menu'
            
            keyboard = [
                [InlineKeyboardButton("➕ Set Filter", callback_data="filter_menu_set")],
                [InlineKeyboardButton("👁️ View Filter", callback_data="filter_menu_view")],
                [InlineKeyboardButton("⏸️ Pause Filter", callback_data="filter_menu_pause")],
                [InlineKeyboardButton("🗑️ Delete Filter", callback_data="filter_menu_delete")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Filter Management\n\nSelect an option:",
                reply_markup=reply_markup
            )
            return
        
        # Delete specific filter by ID
        if query.data.startswith("filter_delete_"):
            filter_id = int(query.data.split('_')[2])
            
            if db.delete_filter_by_id(filter_id, user_id):
                message = "✓ Filter has been deleted."
                logger.info(f"Filter {filter_id} deleted", extra={'user_id': user_id})
            else:
                message = "Error deleting filter. Please try again."
            
            # Show remaining filters or menu
            user_filters = db.get_all_filters(user_id)
            if user_filters:
                message += "\n\n<b>Remaining Filters:</b>\n"
                for idx, uf in enumerate(user_filters, 1):
                    message += f"{idx}. {uf.club_name} - {uf.timetable_name}\n"
            
            keyboard = [
                [InlineKeyboardButton("Back to Menu", callback_data="filter_menu_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        # Apply pause with selected duration (must be checked BEFORE filter_pause_ to avoid collision)
        if query.data.startswith("filter_pause_duration_"):
            from datetime import timedelta
            days = int(query.data.split('_')[3])
            filter_id = context.user_data.get('pause_filter_id')
            
            if not filter_id:
                await query.edit_message_text("Error: filter not found. Please try again.")
                return
            
            paused_until = datetime.now() + timedelta(days=days)
            
            if db.pause_filter(filter_id, user_id, paused_until):
                # Get filter details for the message
                user_filters = db.get_all_filters(user_id)
                paused_filter = next((f for f in user_filters if f.id == filter_id), None)
                filter_name = f"{paused_filter.club_name} - {paused_filter.timetable_name}" if paused_filter else f"Filter #{filter_id}"
                
                message = (
                    f"⏸️ <b>Filter paused!</b>\n\n"
                    f"<b>{filter_name}</b>\n"
                    f"Paused for: {days} day{'s' if days > 1 else ''}\n"
                    f"Resumes: {paused_until.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"<i>The bot won't notify or book classes for this filter until the pause expires.</i>"
                )
                logger.info(f"Filter {filter_id} paused for {days} days until {paused_until}", extra={'user_id': user_id})
            else:
                message = "Error pausing filter. Please try again."
            
            context.user_data.pop('pause_filter_id', None)
            
            keyboard = [
                [InlineKeyboardButton("Back to Menu", callback_data="filter_menu_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        # Pause specific filter - show duration selection
        if query.data.startswith("filter_pause_"):
            filter_id = int(query.data.split('_')[2])
            context.user_data['pause_filter_id'] = filter_id
            
            keyboard = [
                [InlineKeyboardButton("1 day", callback_data="filter_pause_duration_1")],
                [InlineKeyboardButton("3 days", callback_data="filter_pause_duration_3")],
                [InlineKeyboardButton("7 days", callback_data="filter_pause_duration_7")],
                [InlineKeyboardButton("14 days", callback_data="filter_pause_duration_14")],
                [InlineKeyboardButton("21 days", callback_data="filter_pause_duration_21")],
                [InlineKeyboardButton("Cancel", callback_data="filter_menu_pause")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "<b>Select pause duration:</b>\n\n"
                "Filter will be paused and won't notify or auto-book classes during this period.",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        # Unpause specific filter
        if query.data.startswith("filter_unpause_"):
            filter_id = int(query.data.split('_')[2])
            
            if db.unpause_filter(filter_id, user_id):
                user_filters = db.get_all_filters(user_id)
                unpaused_filter = next((f for f in user_filters if f.id == filter_id), None)
                filter_name = f"{unpaused_filter.club_name} - {unpaused_filter.timetable_name}" if unpaused_filter else f"Filter #{filter_id}"
                
                message = (
                    f"▶️ <b>Filter unpaused!</b>\n\n"
                    f"<b>{filter_name}</b>\n\n"
                    f"<i>The bot will now resume notifications and auto-booking for this filter.</i>"
                )
                logger.info(f"Filter {filter_id} manually unpaused", extra={'user_id': user_id})
            else:
                message = "Error unpausing filter. Please try again."
            
            keyboard = [
                [InlineKeyboardButton("Back to Menu", callback_data="filter_menu_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return
        
        # City selection
        if query.data.startswith("filter_city_"):
            city = query.data.split('_', 2)[2]
            
            context.user_data['filter_city'] = city
            
            from config.config import AVAILABLE_CLUBS
            city_data = AVAILABLE_CLUBS.get(city, {})
            
            keyboard = []
            
            # For Warsaw, show districts first
            if city == "Warszawa" and isinstance(next(iter(city_data.values()), None), dict):
                context.user_data['filter_step'] = 'district'
                
                for district in sorted(city_data.keys()):
                    keyboard.append([
                        InlineKeyboardButton(
                            district,
                            callback_data=f"filter_district_{district}"
                        )
                    ])
            else:
                # For other cities, show clubs directly
                context.user_data['filter_step'] = 'club'
                
                for club_name, club_id in sorted(city_data.items()):
                    keyboard.append([
                        InlineKeyboardButton(
                            club_name,
                            callback_data=f"filter_club_{club_id}_{club_name}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            title = f"Select a district in {city}:" if city == "Warszawa" else f"Select a club in {city}:"
            
            await query.edit_message_text(
                title,
                reply_markup=reply_markup
            )
            return
        
        # District selection (Warsaw only)
        if query.data.startswith("filter_district_"):
            district = query.data.split('_', 2)[2]
            city = context.user_data.get('filter_city', 'Warszawa')
            
            context.user_data['filter_district'] = district
            context.user_data['filter_step'] = 'club'
            
            from config.config import AVAILABLE_CLUBS
            city_data = AVAILABLE_CLUBS.get(city, {})
            clubs = city_data.get(district, {})
            
            keyboard = []
            for club_name, club_id in sorted(clubs.items()):
                keyboard.append([
                    InlineKeyboardButton(
                        club_name,
                        callback_data=f"filter_club_{club_id}_{club_name}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Select a club in {district}:",
                reply_markup=reply_markup
            )
            return
        if query.data.startswith("filter_club_"):
            parts = query.data.split('_', 3)
            club_id = int(parts[2])
            club_name = parts[3] if len(parts) > 3 else "Unknown"
            
            context.user_data['filter_club_id'] = club_id
            context.user_data['filter_club_name'] = club_name
            context.user_data['filter_step'] = 'timetable'
            
            logger.info(f"User selected club {club_id} ({club_name})", extra={'user_id': user_id})
            
            # Get timetables for this club
            client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
            if not client.authenticate(user_id):
                await query.edit_message_text("Authentication error. Please try again: /login")
                return
            
            filters = client.get_calendar_filters(zone_id=club_id, user_id=user_id)
            if not filters:
                await query.edit_message_text("Could not load filters from API. Please try again.")
                return
            
            timetables = filters.get('TimeTableFilters', [])
            if not timetables:
                await query.edit_message_text("No classes available for this club.")
                return
            
            # Save timetables to cache
            context.user_data['available_timetables'] = timetables
            
            # Show timetable selection buttons
            keyboard = []
            for idx, timetable in enumerate(timetables):
                tt_name = timetable.get('Name')
                keyboard.append([
                    InlineKeyboardButton(
                        tt_name,
                        callback_data=f"filter_timetable_{idx}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("Back", callback_data="filter_back"),
                InlineKeyboardButton("Cancel", callback_data="filter_cancel")
            ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Selected club: {club_name}\n\nSelect a class type:",
                reply_markup=reply_markup
            )
        
        # Timetable selection
        elif query.data.startswith("filter_timetable_"):
            timetable_idx = int(query.data.split('_')[2])
            available_timetables = context.user_data.get('available_timetables', [])
            
            if timetable_idx < 0 or timetable_idx >= len(available_timetables):
                await query.edit_message_text("Invalid class type selection. Please try again.")
                return
            
            selected_timetable = available_timetables[timetable_idx]
            timetable_id = selected_timetable.get('Id')
            timetable_name = selected_timetable.get('Name')
            
            context.user_data['filter_timetable_id'] = timetable_id
            context.user_data['filter_timetable_name'] = timetable_name
            context.user_data['filter_step'] = 'trainer'
            
            logger.info(f"User selected timetable {timetable_id} ({timetable_name})", extra={'user_id': user_id})
            
            # Get trainers for this specific timetable
            client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
            if not client.authenticate(user_id):
                await query.edit_message_text("Authentication error.")
                return
            
            club_id = context.user_data.get('filter_club_id')
            trainers = client.get_trainers_by_timetable(int(club_id), timetable_id, user_id)
            
            context.user_data['available_trainers'] = trainers
            
            # Show trainer selection (optional)
            keyboard = []
            for idx, trainer in enumerate(trainers):
                tr_name = trainer.get('Name')
                keyboard.append([
                    InlineKeyboardButton(
                        tr_name,
                        callback_data=f"filter_trainer_{idx}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("Any trainer", callback_data="filter_skip_trainer")])
            keyboard.append([InlineKeyboardButton("Back to classes", callback_data="filter_back")])
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select trainer (optional):",
                reply_markup=reply_markup
            )
        
        # Trainer selection
        elif query.data.startswith("filter_trainer_"):
            trainer_idx = int(query.data.split('_')[2])
            available_trainers = context.user_data.get('available_trainers', [])
            
            if trainer_idx < 0 or trainer_idx >= len(available_trainers):
                await query.edit_message_text("Invalid trainer selection. Please try again.")
                return
            
            selected_trainer = available_trainers[trainer_idx]
            trainer_id = selected_trainer.get('Id')
            trainer_name = selected_trainer.get('Name')
            
            context.user_data['filter_trainer_id'] = trainer_id
            context.user_data['filter_trainer_name'] = trainer_name
            context.user_data['filter_step'] = 'weekdays'
            
            logger.info(f"User selected trainer {trainer_id} ({trainer_name})", extra={'user_id': user_id})
            
            # Show weekday selection
            keyboard = [
                [InlineKeyboardButton("🔵 Mon", callback_data="filter_weekday_1"), InlineKeyboardButton("Tue", callback_data="filter_weekday_2"), InlineKeyboardButton("Wed", callback_data="filter_weekday_3")],
                [InlineKeyboardButton("Thu", callback_data="filter_weekday_4"), InlineKeyboardButton("🔵 Fri", callback_data="filter_weekday_5"), InlineKeyboardButton("Sat", callback_data="filter_weekday_6")],
                [InlineKeyboardButton("Sun", callback_data="filter_weekday_7")],
                [InlineKeyboardButton("Skip weekdays", callback_data="filter_skip_weekdays")],
                [InlineKeyboardButton("Back", callback_data="filter_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select days of week (select multiple or skip for all days):\n\n🔵 = selected",
                reply_markup=reply_markup
            )
        
        # Skip trainer
        elif query.data == "filter_skip_trainer":
            context.user_data['filter_trainer_id'] = None
            context.user_data['filter_trainer_name'] = None
            context.user_data['filter_step'] = 'weekdays'
            
            logger.info(f"User skipped trainer selection", extra={'user_id': user_id})
            
            # Show weekday selection
            keyboard = [
                [InlineKeyboardButton("🔵 Mon", callback_data="filter_weekday_1"), InlineKeyboardButton("Tue", callback_data="filter_weekday_2"), InlineKeyboardButton("Wed", callback_data="filter_weekday_3")],
                [InlineKeyboardButton("Thu", callback_data="filter_weekday_4"), InlineKeyboardButton("🔵 Fri", callback_data="filter_weekday_5"), InlineKeyboardButton("Sat", callback_data="filter_weekday_6")],
                [InlineKeyboardButton("Sun", callback_data="filter_weekday_7")],
                [InlineKeyboardButton("Skip weekdays", callback_data="filter_skip_weekdays")],
                [InlineKeyboardButton("Back", callback_data="filter_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select days of week (select multiple or skip for all days):\n\n🔵 = selected",
                reply_markup=reply_markup
            )
        
        # Weekday selection
        elif query.data.startswith("filter_weekday_"):
            weekday_num = int(query.data.split('_')[2])
            current_weekdays = context.user_data.get('filter_weekdays', '')
            
            # Parse current selection
            weekdays_list = [int(d) for d in current_weekdays.split(',') if d] if current_weekdays else []
            
            # Toggle selection
            if weekday_num in weekdays_list:
                weekdays_list.remove(weekday_num)
            else:
                weekdays_list.append(weekday_num)
            
            # Sort and save
            weekdays_list.sort()
            context.user_data['filter_weekdays'] = ','.join(map(str, weekdays_list)) if weekdays_list else None
            
            # Rebuild keyboard with updated selection
            selected = set(weekdays_list)
            keyboard = [
                [
                    InlineKeyboardButton(f"{'🔵 ' if 1 in selected else ''}Mon", callback_data="filter_weekday_1"),
                    InlineKeyboardButton(f"{'🔵 ' if 2 in selected else ''}Tue", callback_data="filter_weekday_2"),
                    InlineKeyboardButton(f"{'🔵 ' if 3 in selected else ''}Wed", callback_data="filter_weekday_3")
                ],
                [
                    InlineKeyboardButton(f"{'🔵 ' if 4 in selected else ''}Thu", callback_data="filter_weekday_4"),
                    InlineKeyboardButton(f"{'🔵 ' if 5 in selected else ''}Fri", callback_data="filter_weekday_5"),
                    InlineKeyboardButton(f"{'🔵 ' if 6 in selected else ''}Sat", callback_data="filter_weekday_6")
                ],
                [InlineKeyboardButton(f"{'🔵 ' if 7 in selected else ''}Sun", callback_data="filter_weekday_7")],
                [InlineKeyboardButton("Continue", callback_data="filter_after_weekdays")],
                [InlineKeyboardButton("Back", callback_data="filter_back")],
                [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select days of week (select multiple or skip for all days):\n\n🔵 = selected",
                reply_markup=reply_markup
            )
        
        # Continue after weekday selection
        elif query.data == "filter_after_weekdays":
            context.user_data['filter_step'] = 'time'
            await show_time_selection(update, context, user_id, query)
        
        # Skip weekdays
        elif query.data == "filter_skip_weekdays":
            context.user_data['filter_weekdays'] = None
            context.user_data['filter_step'] = 'time'
            await show_time_selection(update, context, user_id, query)
        
        # Time interval selection
        elif query.data.startswith("filter_time_"):
            hour_str = query.data.split('_')[2]
            current_times = context.user_data.get('filter_times', '')
            
            # Parse current selection
            times_list = [t for t in current_times.split(',') if t] if current_times else []
            
            # Toggle selection
            if hour_str in times_list:
                times_list.remove(hour_str)
            else:
                times_list.append(hour_str)
            
            # Sort and save
            times_list.sort(key=lambda x: int(x))
            context.user_data['filter_times'] = ','.join(times_list) if times_list else None
            
            # Rebuild keyboard with updated selection
            selected = set(times_list)
            keyboard = []
            
            # 18 intervals: 06:00-22:00 in 3 rows of 6
            hours = list(range(6, 23))  # 6 to 22
            
            for row in range(3):
                row_buttons = []
                for col in range(6):
                    idx = row * 6 + col
                    if idx < len(hours):
                        hour = hours[idx]
                        hour_str_formatted = f"{hour:02d}"
                        is_selected = hour_str_formatted in selected
                        button_text = f"{'🔵 ' if is_selected else ''}{hour:02d}:00"
                        row_buttons.append(
                            InlineKeyboardButton(button_text, callback_data=f"filter_time_{hour_str_formatted}")
                        )
                if row_buttons:
                    keyboard.append(row_buttons)
            
            keyboard.append([InlineKeyboardButton("Continue", callback_data="filter_after_time")])
            keyboard.append([InlineKeyboardButton("Skip time filter", callback_data="filter_skip_time")])
            keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select time intervals (optional - select multiple or skip for any time):\n\n🔵 = selected",
                reply_markup=reply_markup
            )
        
        # Continue after time selection
        elif query.data == "filter_after_time":
            times_str = context.user_data.get('filter_times')
            if times_str:
                times_list = [int(t) for t in times_str.split(',')]
                context.user_data['filter_time_from'] = f"{min(times_list):02d}:00"
                context.user_data['filter_time_to'] = f"{max(times_list):02d}:59"
                # Store selected hours for display in confirmation
                context.user_data['filter_time_hours'] = ','.join(str(h) for h in sorted(times_list))
            else:
                context.user_data['filter_time_from'] = None
                context.user_data['filter_time_to'] = None
                context.user_data['filter_time_hours'] = None
            
            context.user_data['filter_step'] = 'confirm'
            await show_filter_confirmation(update, context, user_id)
        
        # Skip time
        elif query.data == "filter_skip_time":
            context.user_data['filter_time_from'] = None
            context.user_data['filter_time_to'] = None
            context.user_data['filter_time_hours'] = None
            context.user_data['filter_step'] = 'confirm'
            
            # Show confirmation
            await show_filter_confirmation(update, context, user_id)
        
        # Back button
        elif query.data == "filter_back":
            step = context.user_data.get('filter_step')
            
            if step == 'club':
                city = context.user_data.get('filter_city', 'Warszawa')
                
                # If Warsaw, go back to district selection
                if city == "Warszawa":
                    context.user_data['filter_step'] = 'district'
                    
                    from config.config import AVAILABLE_CLUBS
                    city_data = AVAILABLE_CLUBS.get(city, {})
                    
                    keyboard = []
                    for district in sorted(city_data.keys()):
                        keyboard.append([
                            InlineKeyboardButton(
                                district,
                                callback_data=f"filter_district_{district}"
                            )
                        ])
                    
                    keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
                    keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"Select a district in {city}:",
                        reply_markup=reply_markup
                    )
                else:
                    # For other cities, go back to city selection
                    context.user_data['filter_step'] = 'city'
                    context.user_data.pop('filter_city', None)
                    
                    from config.config import AVAILABLE_CLUBS
                    keyboard = []
                    for city_name in sorted(AVAILABLE_CLUBS.keys()):
                        keyboard.append([
                            InlineKeyboardButton(
                                city_name,
                                callback_data=f"filter_city_{city_name}"
                            )
                        ])
                    
                    keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        "Select a city:",
                        reply_markup=reply_markup
                    )
            
            elif step == 'district':
                # Go back to city selection
                context.user_data['filter_step'] = 'city'
                context.user_data.pop('filter_district', None)
                context.user_data.pop('filter_city', None)
                
                from config.config import AVAILABLE_CLUBS
                keyboard = []
                for city in sorted(AVAILABLE_CLUBS.keys()):
                    keyboard.append([
                        InlineKeyboardButton(
                            city,
                            callback_data=f"filter_city_{city}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "Select a city:",
                    reply_markup=reply_markup
                )
            
            elif step == 'timetable':
                # Go back to club selection
                context.user_data['filter_step'] = 'club'
                
                from config.config import AVAILABLE_CLUBS
                city = context.user_data.get('filter_city')
                district = context.user_data.get('filter_district')
                
                # If Warsaw, get clubs from district
                if city == "Warszawa" and district:
                    city_data = AVAILABLE_CLUBS.get(city, {})
                    clubs = city_data.get(district, {})
                else:
                    # For other cities, get clubs directly
                    clubs = AVAILABLE_CLUBS.get(city, {})
                
                keyboard = []
                for club_name, club_id in sorted(clubs.items()):
                    keyboard.append([
                        InlineKeyboardButton(
                            club_name,
                            callback_data=f"filter_club_{club_id}_{club_name}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
                keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Select a club in {city}:",
                    reply_markup=reply_markup
                )
            
            elif step == 'trainer':
                context.user_data['filter_step'] = 'timetable'
                club_name = context.user_data.get('filter_club_name')
                available_timetables = context.user_data.get('available_timetables', [])
                
                # Use cached timetables instead of re-fetching
                keyboard = []
                for idx, timetable in enumerate(available_timetables):
                    tt_name = timetable.get('Name')
                    keyboard.append([
                        InlineKeyboardButton(
                            tt_name,
                            callback_data=f"filter_timetable_{idx}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("Back to club", callback_data="filter_back")])
                keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Select class type for {club_name}:",
                    reply_markup=reply_markup
                )
            
            elif step == 'weekdays':
                # Go back to trainer selection
                context.user_data['filter_step'] = 'trainer'
                club_name = context.user_data.get('filter_club_name')
                available_trainers = context.user_data.get('available_trainers', [])
                
                keyboard = []
                for idx, trainer in enumerate(available_trainers):
                    trainer_name = trainer.get('Name')
                    keyboard.append([
                        InlineKeyboardButton(
                            trainer_name,
                            callback_data=f"filter_trainer_{idx}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("Skip trainer", callback_data="filter_skip_trainer")])
                keyboard.append([InlineKeyboardButton("Back", callback_data="filter_back")])
                keyboard.append([InlineKeyboardButton("Cancel", callback_data="filter_cancel")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Select a trainer for {club_name}:",
                    reply_markup=reply_markup
                )
            
            elif step == 'time':
                # Go back to weekday selection
                context.user_data['filter_step'] = 'weekdays'
                available_trainers = context.user_data.get('available_trainers', [])
                
                # Build keyboard with current selections
                selected = set()
                if context.user_data.get('filter_weekdays'):
                    selected = set(int(d) for d in context.user_data.get('filter_weekdays', '').split(',') if d)
                
                keyboard = [
                    [
                        InlineKeyboardButton(f"{'🔵 ' if 1 in selected else ''}Mon", callback_data="filter_weekday_1"),
                        InlineKeyboardButton(f"{'🔵 ' if 2 in selected else ''}Tue", callback_data="filter_weekday_2"),
                        InlineKeyboardButton(f"{'🔵 ' if 3 in selected else ''}Wed", callback_data="filter_weekday_3")
                    ],
                    [
                        InlineKeyboardButton(f"{'🔵 ' if 4 in selected else ''}Thu", callback_data="filter_weekday_4"),
                        InlineKeyboardButton(f"{'🔵 ' if 5 in selected else ''}Fri", callback_data="filter_weekday_5"),
                        InlineKeyboardButton(f"{'🔵 ' if 6 in selected else ''}Sat", callback_data="filter_weekday_6")
                    ],
                    [InlineKeyboardButton(f"{'🔵 ' if 7 in selected else ''}Sun", callback_data="filter_weekday_7")],
                    [InlineKeyboardButton("Continue", callback_data="filter_after_weekdays")],
                    [InlineKeyboardButton("Back", callback_data="filter_back")],
                    [InlineKeyboardButton("Cancel", callback_data="filter_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "Select days of week (select multiple or skip for all days):\n\n🔵 = selected",
                    reply_markup=reply_markup
                )
        
        # Confirm filters
        elif query.data == "filter_confirm":
            context.user_data['filter_step'] = 'auto_booking'
            
            # Show auto booking question
            keyboard = [
                [InlineKeyboardButton("✓ Yes, enable", callback_data="filter_auto_booking_yes")],
                [InlineKeyboardButton("✗ No, disable", callback_data="filter_auto_booking_no")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Enable automatic booking for this filter?\n\n"
                "When enabled, bot will automatically book available classes matching this filter.",
                reply_markup=reply_markup
            )
        
        # Auto booking decision
        elif query.data == "filter_auto_booking_yes":
            context.user_data['filter_auto_booking'] = True
            await show_reminder_selection(update, context, user_id, query)
        
        elif query.data == "filter_auto_booking_no":
            context.user_data['filter_auto_booking'] = False
            await show_reminder_selection(update, context, user_id, query)
        
        # Training reminder decision
        elif query.data == "filter_reminder_off":
            context.user_data['filter_reminder_minutes'] = None
            await save_filter_to_db(update, context, user_id, query)
        
        elif query.data == "filter_reminder_15":
            context.user_data['filter_reminder_minutes'] = 15
            await save_filter_to_db(update, context, user_id, query)
        
        elif query.data == "filter_reminder_30":
            context.user_data['filter_reminder_minutes'] = 30
            await save_filter_to_db(update, context, user_id, query)
        
        elif query.data == "filter_reminder_60":
            context.user_data['filter_reminder_minutes'] = 60
            await save_filter_to_db(update, context, user_id, query)
        
        # Cancel
        elif query.data == "filter_cancel":
            context.user_data['filter_mode'] = False
            await query.edit_message_text("Filters cancelled.")
    
    @staticmethod
    async def bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bookings command - show user's active bookings from zdrofit API."""
        user_id = update.effective_user.id
        logger.info(f"User viewed bookings", extra={'user_id': user_id})
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please login first: /login")
            return
        
        # Get bookings from zdrofit API instead of database
        client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
        if not client.authenticate(user_id):
            await update.message.reply_text("Authentication error. Please try again: /login")
            return
        
        all_bookings = client.get_user_schedule(user_id)
        
        # NOTE: Filters are NOT applied to already booked classes
        # Users should see all their existing bookings regardless of filter settings
        
        # Filter only active (future) bookings
        now = datetime.now()
        active_bookings = []
        
        for booking in all_bookings:
            start_time_str = booking.get("start_time", "")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    # Keep only future bookings
                    if start_time > now:
                        active_bookings.append(booking)
                except:
                    pass
        
        if not active_bookings:
            await update.message.reply_text("You have no active bookings.")
            return
        
        # Sort by start time
        active_bookings.sort(key=lambda x: x.get("start_time", ""))
        
        # Send header message
        await update.message.reply_text(
            f"<b>Your Active Bookings:</b> ({len(active_bookings)} classes)",
            parse_mode=ParseMode.HTML
        )
        
        # Send each booking as a separate message with cancel button
        for i, booking in enumerate(active_bookings, 1):
            # Parse start_time
            start_time_str = booking.get("start_time", "")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    formatted_time = start_time.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_time = start_time_str
            else:
                formatted_time = "N/A"
            
            trainer = booking.get("trainer", "Unknown")
            club = booking.get("club", "Unknown")
            zone = booking.get("zone", "Unknown")
            class_id = booking.get("class_id")
            is_standby = " (standby)" if booking.get("is_stand_by") else ""
            can_cancel = booking.get("can_cancel", False)

            message = (
                f"<b>{i}. {booking.get('name', 'Unknown')}</b>{is_standby}\n"
                f"Time: {formatted_time}\n"
                f"Gym: {club} • {zone}\n"
                f"Trainer: {trainer}"
            )
            
            # Create keyboard with cancel button, so user can cancel this booking
            if can_cancel and class_id:
                keyboard = [
                    [InlineKeyboardButton("Cancel", callback_data=f"cancel_{class_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    @staticmethod
    async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Logout command."""
        user_id = update.effective_user.id
        logger.info(f"User logged out", extra={'user_id': user_id})
        
        if db.delete_user(user_id):
            await update.message.reply_text(
                "You have successfully logged out.\n"
                "Use /login to login again."
            )
        else:
            await update.message.reply_text("Logout error. Please try again.")
    
    @staticmethod
    async def past_classes(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's past bookings (last 5 classes)."""
        user_id = update.effective_user.id
        logger.info(f"User viewed past bookings", extra={'user_id': user_id})
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please login first: /login")
            return
        
        # Get schedule from zdrofit API
        client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
        if not client.authenticate(user_id):
            await update.message.reply_text("Authentication error. Please try again: /login")
            return
        
        all_bookings = client.get_user_schedule(user_id)
        
        # Filter past bookings (those with start_time in the past)
        now = datetime.now()
        past_bookings = []
        
        for booking in all_bookings:
            start_time_str = booking.get("start_time", "")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    # Keep only past bookings
                    if start_time < now:
                        past_bookings.append(booking)
                except:
                    pass
        
        if not past_bookings:
            await update.message.reply_text("You have no past bookings.")
            return
        
        # Sort by start time descending (newest first) and get last 5
        past_bookings.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        past_bookings = past_bookings[:5]
        
        # Send header message
        await update.message.reply_text(
            f"<b>Your Past Bookings:</b> (Last {len(past_bookings)} classes)",
            parse_mode=ParseMode.HTML
        )
        
        # Send each past booking as a separate message
        for i, booking in enumerate(past_bookings, 1):
            # Parse start_time
            start_time_str = booking.get("start_time", "")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    formatted_time = start_time.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_time = start_time_str
            else:
                formatted_time = "N/A"
            
            trainer = booking.get("trainer", "Unknown")
            club = booking.get("club", "Unknown")
            zone = booking.get("zone", "Unknown")
            is_standby = " (standby)" if booking.get("is_stand_by") else ""

            message = (
                f"<b>{i}. {booking.get('name', 'Unknown')}</b>{is_standby}\n"
                f"Time: {formatted_time}\n"
                f"Gym: {club} • {zone}\n"
                f"Trainer: {trainer}"
            )
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    @staticmethod
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the user's year-wrap (Spotify-Wrapped style) statistics for the current year."""
        user_id = update.effective_user.id
        logger.info(f"User requested year wrap", extra={'user_id': user_id})
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please login first: /login")
            return
        
        client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
        if not client.authenticate(user_id):
            await update.message.reply_text("Authentication error. Please try again: /login")
            return
        
        schedule = client.get_user_schedule(user_id)
        year = datetime.now().year
        stats = compute_year_wrap(schedule, year)
        
        if stats is None:
            await update.message.reply_text(
                f"You haven't attended any classes in {year} yet.\n"
                "Book a class and come back to see your stats! 💪"
            )
            return
        
        message = format_year_wrap_message(stats)
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    @staticmethod
    async def handle_booking_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle booking button clicks."""
        user_id = update.effective_user.id
        query = update.callback_query
        
        try:
            await query.answer()
        except:
            pass  # Ignore if query is already answered or expired
        
        if query.data.startswith("book_"):
            class_id = query.data.replace("book_", "")
            user = db.get_user(user_id)
            
            if not user:
                await query.edit_message_text("Authentication error. Please login: /login")
                return
            
            logger.info(f"User attempting to book class {class_id}", extra={'user_id': user_id})
            
            client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
            if not client.authenticate(user_id):
                await query.edit_message_text("Authentication error")
                return
            
            if client.book_class(class_id, user_id):
                # Save booking to database
                booking = Booking(
                    user_id=user_id,
                    class_id=class_id,
                    title=context.user_data.get(f"class_title_{class_id}", "Unknown"),
                    start_time=context.user_data.get(f"class_time_{class_id}", datetime.now())
                )
                db.add_booking(booking)
                
                await query.edit_message_text(
                    "Class successfully booked!\n\n"
                    "Check all bookings: /bookings"
                )
            else:
                await query.edit_message_text("Booking error. Please try again.")
        
        elif query.data.startswith("cancel_"):
            class_id = query.data.replace("cancel_", "")
            user = db.get_user(user_id)
            
            if not user:
                await query.edit_message_text("Authentication error. Please login: /login")
                return
            
            logger.info(f"User attempting to cancel class {class_id}", extra={'user_id': user_id})
            
            client = ZdrofitAPIClient(user.zdrofit_email, user.zdrofit_password)
            if not client.authenticate(user_id):
                await query.edit_message_text("Authentication error")
                return
            
            if client.cancel_booking(class_id, user_id):
                db.cancel_booking(user_id, class_id)
                await query.edit_message_text(
                    "✓ Booking cancelled successfully.\n\n"
                    "Use /bookings to view your remaining bookings."
                )
            else:
                await query.edit_message_text("Cancellation error. Please try again.")
        
        elif query.data.startswith("skip_"):
            class_id = query.data.replace("skip_", "")
            user = db.get_user(user_id)
            
            if not user:
                await query.edit_message_text("Authentication error. Please login: /login")
                return
            
            logger.info(f"User skipped class {class_id} (marked as not interested)", extra={'user_id': user_id})
            
            # Persist the skip so the scheduler won't notify about this class again
            db.add_skipped_class(user_id, class_id)
            
            # Remove the notification message
            try:
                await query.delete_message()
            except Exception as e:
                logger.error(f"Error deleting message: {str(e)}", extra={'user_id': user_id})
                await query.edit_message_text("Error processing your request.")


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for login flow only, reject all other text inputs."""
    user_id = update.effective_user.id
    
    # Only accept text input during specific login steps
    login_step = context.user_data.get('login_step')
    
    # Accept input ONLY when explicitly expecting email or password
    if login_step == 'email':
        await BotHandlers.handle_email_input(update, context)
    elif login_step == 'password':
        await BotHandlers.handle_password_input(update, context)
    else:
        # Reject any unexpected text input
        logger.warning(f"Rejected unexpected text input from user", extra={'user_id': user_id})
        await update.message.reply_text(
            "❌ Unexpected input. Use available commands:\n"
            "/start - Welcome\n"
            "/login - Login\n"
            "/filters - Set filters\n"
            "/bookings - View bookings\n"
            "/past_classes - View past classes\n"
            "/wrapped - Year in review\n"
            "/logout - Logout"
        )


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a broadcast message to all users. Admin only."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_TELEGRAM_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    message_text = " ".join(context.args) if context.args else ""
    if not message_text:
        await update.message.reply_text(
            "Usage: /broadcast <message>\n\nExample: /broadcast ⚠️ Maintenance scheduled at 10pm."
        )
        return
    
    from src.telegram_bot.notifications import NotificationSender
    
    user_ids = db.get_all_user_telegram_ids()
    if not user_ids:
        await update.message.reply_text("No registered users to broadcast to.")
        return
    
    sender = NotificationSender(bot=context.bot)
    result = await sender.broadcast_message(user_ids, message_text)
    
    await update.message.reply_text(
        f"📢 Broadcast complete.\n✅ Sent: {result['sent']}\n❌ Failed: {result['failed']}"
    )


def setup_bot_handlers(app: Application):
    """Setup all bot command handlers with strict security."""
    
    # Command handlers - ONLY these commands are allowed
    ALLOWED_COMMANDS = {
        "start": BotHandlers.start,
        "login": BotHandlers.login,
        "filters": BotHandlers.filters,
        "bookings": BotHandlers.bookings,
        "past_classes": BotHandlers.past_classes,
        "wrapped": BotHandlers.wrapped,
        "logout": BotHandlers.logout,
        "broadcast": broadcast_command,
    }
    
    for command, handler in ALLOWED_COMMANDS.items():
        app.add_handler(CommandHandler(command, handler))
    
    # Callback handlers - pattern-based for security
    app.add_handler(CallbackQueryHandler(BotHandlers.handle_booking_button, pattern="^(book_|cancel_|skip_)"))
    app.add_handler(CallbackQueryHandler(BotHandlers.handle_filter_callback, pattern="^filter_"))
    
    # Text input handler (for login flow ONLY)
    # Strictly validates input against expected login steps
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
