"""Database connection and operations module."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from config.config import DB_PATH
from src.utils.logger import get_logger
from src.utils.crypto import PasswordEncryptor
from src.database.models import User, UserFilter, AvailableClass, Booking, FilterCatalog

logger = get_logger(__name__)


class Database:
    """SQLite database handler."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database tables."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    zdrofit_email TEXT NOT NULL UNIQUE,
                    zdrofit_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User filters table (updated with club selection and weekdays)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    club_id INTEGER,
                    club_name TEXT,
                    zone_id TEXT,
                    zone_name TEXT,
                    timetable_id TEXT,
                    timetable_name TEXT,
                    category_id TEXT,
                    category_name TEXT,
                    trainer_id TEXT,
                    trainer_name TEXT,
                    time_from TEXT,
                    time_to TEXT,
                    weekdays TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            ''')
            
            # Filter catalog (cache for filter options)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS filter_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id TEXT,
                    zone_name TEXT,
                    filter_type TEXT,
                    data TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(zone_id, filter_type)
                )
            ''')
            
            # Available classes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS available_classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    class_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    gym_name TEXT,
                    trainer_name TEXT,
                    activity_type TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    available_spots INTEGER,
                    notified_at TIMESTAMP,
                    skipped INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, class_id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            ''')
            
            # Bookings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    class_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    start_time TIMESTAMP,
                    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cancelled_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, class_id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    # User operations
    def add_user(self, user: User) -> bool:
        """Add or update user with encrypted password."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Encrypt password before storing
            encrypted_password = PasswordEncryptor.encrypt(user.zdrofit_password)
            
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (telegram_id, zdrofit_email, zdrofit_password, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (user.telegram_id, user.zdrofit_email, encrypted_password, datetime.now()))
            conn.commit()
            conn.close()
            logger.info(f"User added/updated", extra={'user_id': user.telegram_id})
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}", extra={'user_id': getattr(user, 'telegram_id', 'unknown')})
            return False
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID with decrypted password."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Decrypt password when retrieving
                decrypted_password = PasswordEncryptor.decrypt(row['zdrofit_password'])
                return User(
                    telegram_id=row['telegram_id'],
                    zdrofit_email=row['zdrofit_email'],
                    zdrofit_password=decrypted_password,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}", extra={'user_id': telegram_id})
            return None
    
    def delete_user(self, telegram_id: int) -> bool:
        """Delete user (logout)."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
            conn.commit()
            conn.close()
            logger.info(f"User deleted (logout)", extra={'user_id': telegram_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}", extra={'user_id': telegram_id})
            return False
    
    def get_all_users(self) -> List[User]:
        """Get all users with decrypted passwords."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            rows = cursor.fetchall()
            conn.close()
            
            users = []
            for row in rows:
                # Decrypt password when retrieving
                decrypted_password = PasswordEncryptor.decrypt(row['zdrofit_password'])
                users.append(User(
                    telegram_id=row['telegram_id'],
                    zdrofit_email=row['zdrofit_email'],
                    zdrofit_password=decrypted_password,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    # User filter operations
    def add_filter(self, user_filter: UserFilter) -> bool:
        """Add or update user filter."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete old filter and add new one
            cursor.execute('DELETE FROM user_filters WHERE user_id = ?', (user_filter.user_id,))
            
            cursor.execute('''
                INSERT INTO user_filters 
                (user_id, gym_id, trainer_id, activity_type, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_filter.user_id, user_filter.gym_id, user_filter.trainer_id, 
                  user_filter.activity_type, datetime.now()))
            conn.commit()
            conn.close()
            logger.info(f"Filter updated", extra={'user_id': user_filter.user_id})
            return True
        except Exception as e:
            logger.error(f"Error adding filter: {e}", extra={'user_id': user_filter.user_id})
            return False
    
    def get_filter(self, user_id: int) -> Optional[UserFilter]:
        """Get user filters."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_filters WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return UserFilter(
                    id=row['id'],
                    user_id=row['user_id'],
                    gym_id=row['gym_id'],
                    trainer_id=row['trainer_id'],
                    activity_type=row['activity_type'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            return None
        except Exception as e:
            logger.error(f"Error getting filter: {e}", extra={'user_id': user_id})
            return None
    
    # Available classes operations
    def add_available_class(self, available_class: AvailableClass) -> bool:
        """Add or update available class."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO available_classes 
                (user_id, class_id, title, gym_name, trainer_name, activity_type, 
                 start_time, end_time, available_spots, notified_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (available_class.user_id, available_class.class_id, available_class.title,
                  available_class.gym_name, available_class.trainer_name, available_class.activity_type,
                  available_class.start_time, available_class.end_time, available_class.available_spots,
                  available_class.notified_at, datetime.now()))
            conn.commit()
            conn.close()
            logger.info(f"Available class added", extra={'user_id': available_class.user_id})
            return True
        except Exception as e:
            logger.error(f"Error adding available class: {e}", extra={'user_id': available_class.user_id})
            return False
    
    def mark_class_notified(self, user_id: int, class_id: str) -> bool:
        """Mark class as notified."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE available_classes 
                SET notified_at = ?, updated_at = ?
                WHERE user_id = ? AND class_id = ?
            ''', (datetime.now(), datetime.now(), user_id, class_id))
            conn.commit()
            conn.close()
            logger.info(f"Class marked as notified", extra={'user_id': user_id})
            return True
        except Exception as e:
            logger.error(f"Error marking class as notified: {e}", extra={'user_id': user_id})
            return False
    
    def get_unnotified_classes(self, user_id: int) -> List[AvailableClass]:
        """Get classes that haven't been notified yet."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM available_classes 
                WHERE user_id = ? AND notified_at IS NULL
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            classes = []
            for row in rows:
                classes.append(AvailableClass(
                    id=row['id'],
                    user_id=row['user_id'],
                    class_id=row['class_id'],
                    title=row['title'],
                    gym_name=row['gym_name'],
                    trainer_name=row['trainer_name'],
                    activity_type=row['activity_type'],
                    start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
                    end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                    available_spots=row['available_spots'],
                    notified_at=datetime.fromisoformat(row['notified_at']) if row['notified_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                ))
            return classes
        except Exception as e:
            logger.error(f"Error getting unnotified classes: {e}", extra={'user_id': user_id})
            return []
    
    # Booking operations
    def add_booking(self, booking: Booking) -> bool:
        """Add or update booking."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bookings 
                (user_id, class_id, title, start_time, booked_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (booking.user_id, booking.class_id, booking.title, 
                  booking.start_time, datetime.now(), datetime.now()))
            conn.commit()
            conn.close()
            logger.info(f"Booking added", extra={'user_id': booking.user_id})
            return True
        except Exception as e:
            logger.error(f"Error adding booking: {e}", extra={'user_id': booking.user_id})
            return False
    
    def cancel_booking(self, user_id: int, class_id: str) -> bool:
        """Cancel booking."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE bookings 
                SET cancelled_at = ?, updated_at = ?
                WHERE user_id = ? AND class_id = ? AND cancelled_at IS NULL
            ''', (datetime.now(), datetime.now(), user_id, class_id))
            conn.commit()
            conn.close()
            logger.info(f"Booking cancelled", extra={'user_id': user_id})
            return True
        except Exception as e:
            logger.error(f"Error cancelling booking: {e}", extra={'user_id': user_id})
            return False
    
    def get_user_bookings(self, user_id: int) -> List[Booking]:
        """Get active user bookings."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bookings 
                WHERE user_id = ? AND cancelled_at IS NULL
                ORDER BY start_time
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            bookings = []
            for row in rows:
                bookings.append(Booking(
                    id=row['id'],
                    user_id=row['user_id'],
                    class_id=row['class_id'],
                    title=row['title'],
                    start_time=datetime.fromisoformat(row['start_time']),
                    booked_at=datetime.fromisoformat(row['booked_at']),
                    cancelled_at=datetime.fromisoformat(row['cancelled_at']) if row['cancelled_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return bookings
        except Exception as e:
            logger.error(f"Error getting user bookings: {e}", extra={'user_id': user_id})
            return []
    
    def is_class_booked(self, user_id: int, class_id: str) -> bool:
        """Check if class is already booked."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bookings 
                WHERE user_id = ? AND class_id = ? AND cancelled_at IS NULL
            ''', (user_id, class_id))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking booking: {e}", extra={'user_id': user_id})
            return False
    
    def mark_class_skipped(self, user_id: int, class_id: str) -> bool:
        """Mark class as skipped (not interested) to avoid showing it again."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if class already exists in available_classes
            cursor.execute('''
                SELECT id FROM available_classes 
                WHERE user_id = ? AND class_id = ?
            ''', (user_id, class_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record to mark as skipped
                cursor.execute('''
                    UPDATE available_classes 
                    SET skipped = 1, updated_at = datetime('now')
                    WHERE user_id = ? AND class_id = ?
                ''', (user_id, class_id))
            else:
                # Insert minimal record if not exists
                cursor.execute('''
                    INSERT INTO available_classes 
                    (user_id, class_id, title, skipped, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                ''', (user_id, class_id, "Skipped Class"))
            
            conn.commit()
            conn.close()
            logger.info(f"Marked class {class_id} as skipped for user", 
                       extra={'user_id': user_id})
            return True
        except Exception as e:
            logger.error(f"Error marking class as skipped: {e}", 
                        extra={'user_id': user_id})
            return False
    
    def is_class_skipped(self, user_id: int, class_id: str) -> bool:
        """Check if class is marked as skipped."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM available_classes 
                WHERE user_id = ? AND class_id = ? AND skipped = 1
            ''', (user_id, class_id))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if class skipped: {e}", 
                        extra={'user_id': user_id})
            return False
    
    # ==================== Filter Management ====================
    
    def add_filter(self, user_filter: 'UserFilter') -> bool:
        """Add new user filter (max 3 per user)."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check how many filters user already has
            cursor.execute(
                'SELECT COUNT(*) as count FROM user_filters WHERE user_id = ?',
                (user_filter.user_id,)
            )
            result = cursor.fetchone()
            filter_count = result['count'] if result else 0
            
            # Reject if already has 3 filters
            if filter_count >= 3:
                logger.warning(f"User already has 3 filters, cannot add more", 
                              extra={'user_id': user_filter.user_id})
                conn.close()
                return False
            
            # Insert new filter (don't delete old ones)
            cursor.execute('''
                INSERT INTO user_filters 
                (user_id, club_id, club_name, zone_id, zone_name, timetable_id, timetable_name, 
                 category_id, category_name, trainer_id, trainer_name, time_from, time_to, weekdays)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_filter.user_id,
                user_filter.club_id,
                user_filter.club_name,
                user_filter.zone_id,
                user_filter.zone_name,
                user_filter.timetable_id,
                user_filter.timetable_name,
                user_filter.category_id,
                user_filter.category_name,
                user_filter.trainer_id,
                user_filter.trainer_name,
                user_filter.time_from,
                user_filter.time_to,
                user_filter.weekdays
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Filter added for user {user_filter.user_id} (total: {filter_count + 1})", 
                       extra={'user_id': user_filter.user_id})
            return True
        except Exception as e:
            logger.error(f"Error saving filter: {e}", extra={'user_id': user_filter.user_id})
            return False
    
    def get_filter(self, user_id: int) -> Optional['UserFilter']:
        """Get first user filter (backwards compatibility). Use get_all_filters() for all filters."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM user_filters WHERE user_id = ? ORDER BY created_at ASC LIMIT 1',
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            from src.database.models import UserFilter
            return UserFilter(
                id=row['id'],
                user_id=row['user_id'],
                club_id=row['club_id'],
                club_name=row['club_name'],
                zone_id=row['zone_id'],
                zone_name=row['zone_name'],
                timetable_id=row['timetable_id'],
                timetable_name=row['timetable_name'],
                category_id=row['category_id'],
                category_name=row['category_name'],
                trainer_id=row['trainer_id'],
                trainer_name=row['trainer_name'],
                time_from=row['time_from'],
                time_to=row['time_to'],
                weekdays=row['weekdays'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
            )
        except Exception as e:
            logger.error(f"Error getting filter: {e}", extra={'user_id': user_id})
            return None
    
    def get_all_filters(self, user_id: int) -> list:
        """Get all filters for user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM user_filters WHERE user_id = ? ORDER BY created_at ASC',
                (user_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return []
            
            from src.database.models import UserFilter
            filters = []
            for row in rows:
                filters.append(UserFilter(
                    id=row['id'],
                    user_id=row['user_id'],
                    club_id=row['club_id'],
                    club_name=row['club_name'],
                    zone_id=row['zone_id'],
                    zone_name=row['zone_name'],
                    timetable_id=row['timetable_id'],
                    timetable_name=row['timetable_name'],
                    category_id=row['category_id'],
                    category_name=row['category_name'],
                    trainer_id=row['trainer_id'],
                    trainer_name=row['trainer_name'],
                    time_from=row['time_from'],
                    time_to=row['time_to'],
                    weekdays=row['weekdays'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                ))
            return filters
        except Exception as e:
            logger.error(f"Error getting all filters: {e}", extra={'user_id': user_id})
            return []
    
    def delete_filter(self, user_id: int) -> bool:
        """Delete all filters for user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_filters WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            logger.info(f"All filters deleted for user {user_id}", extra={'user_id': user_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting filters: {e}", extra={'user_id': user_id})
            return False
    
    def delete_filter_by_id(self, filter_id: int, user_id: int) -> bool:
        """Delete specific filter by ID (user_id for security check)."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_filters WHERE id = ? AND user_id = ?',
                (filter_id, user_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"Filter {filter_id} deleted for user {user_id}", extra={'user_id': user_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting filter: {e}", extra={'user_id': user_id})
            return False
    
    # ==================== Filter Catalog (Cache) ====================
    
    def save_filter_catalog(self, zone_id: str, zone_name: str, filter_type: str, data: str, expires_at: datetime = None) -> bool:
        """Save filter catalog (cache for filter options)."""
        try:
            from datetime import timedelta
            if expires_at is None:
                expires_at = datetime.now() + timedelta(hours=24)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO filter_catalog 
                (zone_id, zone_name, filter_type, data, cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (zone_id, zone_name, filter_type, data, datetime.now(), expires_at))
            
            conn.commit()
            conn.close()
            logger.debug(f"Saved {filter_type} catalog for zone {zone_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving filter catalog: {e}")
            return False
    
    def get_filter_catalog(self, zone_id: str, filter_type: str) -> Optional[str]:
        """Get filter catalog from cache if not expired."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT data, expires_at FROM filter_catalog 
                WHERE zone_id = ? AND filter_type = ?
            ''', (zone_id, filter_type))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Check if cache is expired
            expires_at = datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
            if expires_at and datetime.now() > expires_at:
                logger.debug(f"Cache expired for {filter_type} in zone {zone_id}")
                return None
            
            return row['data']
        except Exception as e:
            logger.error(f"Error getting filter catalog: {e}")
            return None
    
    def invalidate_filter_catalog(self, zone_id: str = None, filter_type: str = None) -> bool:
        """Invalidate filter catalog cache."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if zone_id and filter_type:
                cursor.execute('''
                    DELETE FROM filter_catalog 
                    WHERE zone_id = ? AND filter_type = ?
                ''', (zone_id, filter_type))
            elif zone_id:
                cursor.execute('DELETE FROM filter_catalog WHERE zone_id = ?', (zone_id,))
            else:
                cursor.execute('DELETE FROM filter_catalog')
            
            conn.commit()
            conn.close()
            logger.debug(f"Invalidated filter catalog cache (zone={zone_id}, type={filter_type})")
            return True
        except Exception as e:
            logger.error(f"Error invalidating filter catalog: {e}")
            return False

