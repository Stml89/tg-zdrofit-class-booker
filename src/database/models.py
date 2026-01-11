"""Database models for the zdrofit bot."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from src.utils.crypto import PasswordEncryptor


@dataclass
class User:
    """User model with encrypted password storage."""
    telegram_id: int
    zdrofit_email: str
    zdrofit_password: str  # Encrypted password
    created_at: datetime = None
    updated_at: datetime = None
    _password_encrypted: bool = False  # Track if password is already encrypted
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def encrypt_password(self) -> None:
        """Encrypt password if not already encrypted."""
        if not self._password_encrypted and self.zdrofit_password:
            self.zdrofit_password = PasswordEncryptor.encrypt(self.zdrofit_password)
            self._password_encrypted = True
    
    def get_decrypted_password(self) -> str:
        """Get decrypted password for API calls."""
        if self._password_encrypted:
            return PasswordEncryptor.decrypt(self.zdrofit_password)
        return self.zdrofit_password


@dataclass
class UserFilter:
    """User filter preferences model with gym-dependent activities."""
    id: Optional[int] = None
    user_id: int = None
    club_id: Optional[int] = None              # 7 or 75 (club ID) - required
    club_name: Optional[str] = None            # "Zdrofit Bemowo Dywizjonu 303" (for convenience)
    zone_id: Optional[str] = None              # "10" (zone ID from API) - required
    zone_name: Optional[str] = None            # "Zdrofit Bemowo" (for convenience)
    timetable_id: Optional[str] = None         # "104" (timetable/class type ID) - required
    timetable_name: Optional[str] = None       # "ABS (Brzuch) - MiniClass" (for convenience)
    category_id: Optional[str] = None          # "12" (category ID from API)
    category_name: Optional[str] = None        # "Mini Class" (for convenience)
    trainer_id: Optional[str] = None           # "185" (trainer ID from API) - optional
    trainer_name: Optional[str] = None         # "ADAM CIEŚLAK" (for convenience)
    time_from: Optional[str] = None            # "07:00" (optional)
    time_to: Optional[str] = None              # "20:00" (optional)
    weekdays: Optional[str] = None             # "1,2,3,4,5" (Monday=1...Sunday=7) - optional, comma-separated
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class AvailableClass:
    """Available class model."""
    id: Optional[int] = None
    user_id: int = None
    class_id: str = None  # Unique class ID from API
    title: str = None
    gym_name: str = None
    trainer_name: str = None
    activity_type: str = None
    start_time: datetime = None
    end_time: datetime = None
    available_spots: int = None
    notified_at: Optional[datetime] = None  # When user was notified
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class FilterCatalog:
    """Cache for calendar filter options from API."""
    id: Optional[int] = None
    zone_id: str = None                     # "10"
    zone_name: str = None                   # "Zdrofit Bemowo" (for convenience)
    filter_type: str = None                 # "trainers", "categories", "timetables", "zones"
    data: str = None                        # JSON: [{"Id": "185", "Name": "ADAM..."}, ...]
    cached_at: datetime = None
    expires_at: datetime = None             # Expiry time (24 hours)
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        from datetime import timedelta
        if self.cached_at is None:
            self.cached_at = datetime.now()
        if self.expires_at is None:
            self.expires_at = datetime.now() + timedelta(hours=24)
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class Booking:
    """Booking model."""
    id: Optional[int] = None
    user_id: int = None
    class_id: str = None  # Unique class ID from API
    title: str = None
    start_time: datetime = None
    booked_at: datetime = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
