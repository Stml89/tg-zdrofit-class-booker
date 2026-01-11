"""zdrofit API client - Unofficial Python implementation."""

import requests
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import json
import time
from src.utils.logger import get_logger
from config.config import ZDROFIT_API_BASE_URL, SEARCH_WINDOW_HOURS

if TYPE_CHECKING:
    from src.database.models import UserFilter

logger = get_logger(__name__)

# Constants
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
AUTH_COOKIE_NAME = "ClientPortal.Auth.bak"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2  # Start with 2 seconds, will double each retry


class ZdrofitAPIClient:
    """Client for zdrofit API based on gozdrofit-api (Go implementation)."""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.base_url = ZDROFIT_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        })
        self.authenticated = False
        self.user_id = None
        self.home_club_id = None
    
    def authenticate(self, user_id: int = None) -> bool:
        """
        Authenticate with zdrofit API with retry logic.
        Uses cookies for session management (like the Go implementation).
        
        POST /ClientPortal2/Auth/Login
        Request: {"RememberMe": true, "Login": "email@example.com", "Password": "password"}
        Response: {"User": {"Member": {"Id": ..., "HomeClubId": ..., ...}}, "State": "Classes"}
        """
        url = f"{self.base_url}/ClientPortal2/Auth/Login"
        payload = {
            "RememberMe": True,
            "Login": self.email,
            "Password": self.password
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"POST {url} (attempt {attempt + 1}/{MAX_RETRIES})", extra={'user_id': user_id or 'unknown'})
                logger.debug(f"Request body: {json.dumps({k: v if k != 'Password' else '***' for k, v in payload.items()})}", 
                            extra={'user_id': user_id or 'unknown'})
                
                response = self.session.post(url, json=payload, timeout=10)
                
                logger.debug(f"Response status: {response.status_code}", extra={'user_id': user_id or 'unknown'})
                logger.debug(f"Response body: {response.text}", extra={'user_id': user_id or 'unknown'})
                
                if response.status_code == 200:
                    data = response.json()
                    user = data.get("User", {}).get("Member", {})
                    self.user_id = user.get("Id")
                    self.home_club_id = user.get("HomeClubId")
                    self.authenticated = True
                    logger.info(f"Successfully authenticated with zdrofit (User ID: {self.user_id})", 
                               extra={'user_id': user_id or 'unknown'})
                    return True
                elif response.status_code == 500 and attempt < MAX_RETRIES - 1:
                    # Server error - retry with exponential backoff
                    delay = RETRY_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(f"Server error (500) during authentication, retrying in {delay} seconds", 
                                  extra={'user_id': user_id or 'unknown'})
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Authentication failed: {response.status_code} - {response.text}", 
                                extra={'user_id': user_id or 'unknown'})
                    return False
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(f"Request timeout during authentication, retrying in {delay} seconds", 
                                  extra={'user_id': user_id or 'unknown'})
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Authentication timeout after {MAX_RETRIES} attempts", 
                                extra={'user_id': user_id or 'unknown'})
                    return False
            except Exception as e:
                logger.error(f"Authentication error: {str(e)}", extra={'user_id': user_id or 'unknown'})
                return False
        
        return False
    
    def get_available_classes(self, user_id: int = None, club_id: int = None, timetable_id: str = None, club_name: str = None) -> List[Dict]:
        """
        Get available classes for a specific date and club.
        
        POST /ClientPortal2/Classes/ClassCalendar/DailyClasses
        Request: {"clubId": 7, "date": "YYYY-MM-DD", "categoryId": null, "timeTableId": "20", "trainerId": null, "zoneId": null}
        Response: {"CalendarData": [...], "PagerData": {...}}
        """
        if not self.authenticated:
            logger.error("Not authenticated. Cannot get available classes.", extra={'user_id': user_id or 'unknown'})
            return []
        
        try:
            # Use provided club_id or default to 7
            target_club_id = club_id or 7
            target_timetable_id = timetable_id or "20"
            
            available_classes = []

            # Calculate the time window: current time + 48 hours
            now = datetime.now()
            end_datetime = now + timedelta(hours=SEARCH_WINDOW_HOURS)
            
            # Start from today at 00:00 and go day by day
            current_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            logger.debug(f"Checking classes from {now} to {end_datetime}", extra={'user_id': user_id or 'unknown'})
            
            while current_date.date() <= end_datetime.date():
                url = f"{self.base_url}/ClientPortal2/Classes/ClassCalendar/DailyClasses"
                payload = {
                    "clubId": target_club_id,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "categoryId": None,
                    "timeTableId": target_timetable_id,
                    "trainerId": None,
                    "zoneId": None
                }
                logger.debug(f"POST {url} for date {current_date.date()}", extra={'user_id': user_id or 'unknown'})
                logger.debug(f"Request body: {json.dumps(payload)}", extra={'user_id': user_id or 'unknown'})
                
                response = self.session.post(url, json=payload)
                
                logger.debug(f"Response status: {response.status_code}", extra={'user_id': user_id or 'unknown'})
                if response.status_code == 200:
                    logger.debug(f"Response body: {response.text}", extra={'user_id': user_id or 'unknown'})
                
                if response.status_code == 200:
                    data = response.json()
                    calendar_data = data.get("CalendarData", [])
                    
                    for hour_data in calendar_data:
                        classes = hour_data.get("Classes", [])
                        for cls in classes:
                            # Only available for booking
                            if cls.get("Status") == "Bookable":
                                available_classes.append({
                                    "id": cls.get("Id"),
                                    "title": cls.get("Name"),
                                    "activity_type": cls.get("Name"),  # Use class name as activity type
                                    "start_time": cls.get("StartTime"),
                                    "end_time": cls.get("StartTime"),  # Will be calculated in notification
                                    "duration": cls.get("Duration"),
                                    "status": cls.get("Status"),
                                    "trainer_name": cls.get("Trainer", {}).get("Name") if isinstance(cls.get("Trainer"), dict) else cls.get("Trainer"),
                                    "gym_name": club_name or "Zdrofit",  # Use provided club name or default
                                    "booking_indicator": cls.get("BookingIndicator", {}),
                                    "available_spots": cls.get("BookingIndicator", {}).get("Available", 0)
                                })
                else:
                    logger.error(f"Failed to get classes for {current_date.date()}: {response.status_code} - {response.text[:500]}", 
                                extra={'user_id': user_id or 'unknown'})
                
                current_date += timedelta(days=1)
            
            logger.info(f"Retrieved {len(available_classes)} available bookable classes (club_id={target_club_id}, timetable_id={target_timetable_id})", 
                       extra={'user_id': user_id or 'unknown'})
            return available_classes
        except Exception as e:
            logger.error(f"Error getting available classes: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return [] 

    def get_user_schedule(self, user_id: int = None) -> List[Dict]:
        """
        Get user's booked classes using MyCalendar API.
        
        GET /ClientPortal2/MyCalendar/MyCalendar/GetCalendar
        Response: {"RecentItems": {...}, "FutureItems": {...}, "PastItems": {...}}
        """
        if not self.authenticated:
            logger.error("Not authenticated. Cannot get user schedule.", extra={'user_id': user_id or 'unknown'})
            return []
        
        try:
            url = f"{self.base_url}/ClientPortal2/MyCalendar/MyCalendar/GetCalendar"
            logger.debug(f"GET {url}", extra={'user_id': user_id or 'unknown'})
            
            booked_classes = []
            
            response = self.session.get(url)
            
            logger.debug(f"Response status: {response.status_code}", extra={'user_id': user_id or 'unknown'})
            if response.status_code == 200:
                logger.debug(f"Response body: {response.text}", extra={'user_id': user_id or 'unknown'})
            
            if response.status_code == 200:
                data = response.json()
                
                # Collect classes from Recent, Future, and Past items
                all_items = []
                if "RecentItems" in data and "Items" in data["RecentItems"]:
                    all_items.extend(data["RecentItems"]["Items"])
                    logger.debug(f"Found {len(data['RecentItems']['Items'])} recent items", extra={'user_id': user_id or 'unknown'})
                if "FutureItems" in data and "Items" in data["FutureItems"]:
                    all_items.extend(data["FutureItems"]["Items"])
                    logger.debug(f"Found {len(data['FutureItems']['Items'])} future items", extra={'user_id': user_id or 'unknown'})
                if "PastItems" in data and "Items" in data["PastItems"]:
                    all_items.extend(data["PastItems"]["Items"])
                    logger.debug(f"Found {len(data['PastItems']['Items'])} past items", extra={'user_id': user_id or 'unknown'})
                
                for item in all_items:
                    # Only include GroupClass items that the user is part of
                    if item.get("Type") == "GroupClass":
                        booked_classes.append({
                            "class_id": item.get("Id"),
                            "name": item.get("Name"),
                            "start_time": item.get("StartTime"),
                            "end_time": item.get("EndTime"),
                            "club": item.get("Club"),
                            "zone": item.get("Zone"),
                            "trainer": item.get("TrainerDisplayName"),
                            "can_cancel": item.get("CanCancel", False),
                            "is_stand_by": item.get("IsStandBy", False)
                        })
                
                logger.info(f"Retrieved {len(booked_classes)} booked classes from MyCalendar API", 
                           extra={'user_id': user_id or 'unknown'})
                return booked_classes
            else:
                logger.error(f"Failed to get user schedule: {response.status_code} - {response.text[:500]}", 
                            extra={'user_id': user_id or 'unknown'})
                return []
        except Exception as e:
            logger.error(f"Error getting user schedule: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return []
    
    def book_class(self, class_id: int, user_id: int = None) -> bool:
        """
        Book a class.
        POST /ClientPortal2/Classes/ClassCalendar/BookClass
        Request: {"classId": 1}
        """
        if not self.authenticated:
            logger.error("Not authenticated. Cannot book class.", extra={'user_id': user_id or 'unknown'})
            return False
        
        try:
            url = f"{self.base_url}/ClientPortal2/Classes/ClassCalendar/BookClass"
            payload = {"classId": class_id}
            logger.debug(f"POST {url}", extra={'user_id': user_id or 'unknown'})
            logger.debug(f"Request body: {json.dumps(payload)}", extra={'user_id': user_id or 'unknown'})
            
            response = self.session.post(url, json=payload)
            
            logger.debug(f"Response status: {response.status_code}", extra={'user_id': user_id or 'unknown'})
            logger.debug(f"{response.text[:500]}", extra={'user_id': user_id or 'unknown'})
            
            if response.status_code == 200:
                logger.info(f"Successfully booked class {class_id}", extra={'user_id': user_id or 'unknown'})
                return True
            else:
                logger.error(f"Failed to book class: {response.status_code} - {response.text}", 
                            extra={'user_id': user_id or 'unknown'})
                return False
        except Exception as e:
            logger.error(f"Error booking class: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return False
    
    def cancel_booking(self, class_id: int, user_id: int = None) -> bool:
        """
        Cancel a booking.
        POST /ClientPortal2/Classes/ClassCalendar/CancelBooking
        Request: {"classId": 1}
        """
        if not self.authenticated:
            logger.error("Not authenticated. Cannot cancel booking.", extra={'user_id': user_id or 'unknown'})
            return False
        
        try:
            url = f"{self.base_url}/ClientPortal2/Classes/ClassCalendar/CancelBooking"
            payload = {"classId": class_id}
            logger.debug(f"POST {url}", extra={'user_id': user_id or 'unknown'})
            logger.debug(f"Request body: {json.dumps(payload)}", extra={'user_id': user_id or 'unknown'})
            
            response = self.session.post(url, json=payload)
            
            logger.debug(f"Response status: {response.status_code}", extra={'user_id': user_id or 'unknown'})
            logger.debug(f"Response body: {response.text}", extra={'user_id': user_id or 'unknown'})
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully cancelled booking for class {class_id}", extra={'user_id': user_id or 'unknown'})
                return True
            else:
                logger.error(f"Failed to cancel booking: {response.status_code} - {response.text}", 
                            extra={'user_id': user_id or 'unknown'})
                return False
        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return False
    
    def get_trainers_by_timetable(self, club_id: int, timetable_id: str, user_id: int = None) -> List[Dict]:
        """
        Get trainers available for a specific timetable/class type in a club.
        Fetches weekly schedule using WeeklyClasses endpoint and extracts unique trainers.
        
        POST /ClientPortal2/Classes/ClassCalendar/WeeklyClasses
        Returns list of trainers: [{"Id": "185", "Name": "ADAM CIEŚLAK"}, ...]
        """
        if not self.authenticated:
            logger.error("Not authenticated. Cannot get trainers by timetable.", extra={'user_id': user_id or 'unknown'})
            return []
        
        try:
            url = f"{self.base_url}/ClientPortal2/Classes/ClassCalendar/WeeklyClasses"
            
            payload = {
                "clubId": club_id,
                "categoryId": None,
                "timeTableId": timetable_id,
                "trainerId": None,
                "zoneId": None,
                "daysInWeek": 7
            }
            
            logger.debug(f"Fetching weekly classes for timetable {timetable_id} in club {club_id}", 
                       extra={'user_id': user_id or 'unknown'})
            
            response = self.session.post(url, json=payload)
            
            if response.status_code != 200:
                logger.error(f"API error getting weekly classes: {response.status_code}", 
                           extra={'user_id': user_id or 'unknown'})
                return []
            
            data = response.json()
            calendar_data = data.get("CalendarData", [])
            trainers_dict = {}  # Use dict to avoid duplicates: {Name: {Id, Name}}
            
            # Iterate through zones
            for zone_data in calendar_data:
                classes_per_hour = zone_data.get("ClassesPerHour", [])
                
                # Iterate through time slots
                for hour_block in classes_per_hour:
                    classes_per_day = hour_block.get("ClassesPerDay", [])
                    
                    # Iterate through days
                    for day_classes in classes_per_day:
                        # Each day can have multiple classes at same time
                        for cls in day_classes:
                            trainer_name = cls.get("Trainer", "").strip()
                            
                            # Only add non-empty trainer names
                            if trainer_name:
                                # Use trainer name as key to deduplicate
                                # API doesn't provide trainer ID, so we use the name as ID
                                trainers_dict[trainer_name] = {
                                    "Id": trainer_name,
                                    "Name": trainer_name
                                }
            
            trainers_list = sorted(list(trainers_dict.values()), key=lambda x: x["Name"])
            logger.info(f"Retrieved {len(trainers_list)} unique trainers for timetable {timetable_id}: {[t['Name'] for t in trainers_list]}", 
                       extra={'user_id': user_id or 'unknown'})
            return trainers_list
        
        except Exception as e:
            logger.error(f"Error getting trainers by timetable: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return []
    
    def get_calendar_filters(self, zone_id: int = None, user_id: int = None) -> Dict:
        """
        Get calendar filters (zones, categories, trainers, timetables).
        
        POST /ClientPortal2/Classes/ClassCalendar/GetCalendarFilters
        Request: {"clubId": 7}
        Response: {
            "TrainerFilters": [...],
            "CategoryFilters": [...],
            "ZoneFilters": [...],
            "TimeTableFilters": [...],
            "ActivityCategoryFilters": [...]
        }
        """
        if not self.authenticated:
            logger.error("Not authenticated. Cannot get calendar filters.", extra={'user_id': user_id or 'unknown'})
            return {}
        
        try:
            url = f"{self.base_url}/ClientPortal2/Classes/ClassCalendar/GetCalendarFilters"
            
            # If no zone_id provided, use home club ID
            club_id = zone_id or self.home_club_id or 7  # Default to 7
            
            payload = {"clubId": club_id}
            logger.debug(f"POST {url}", extra={'user_id': user_id or 'unknown'})
            logger.debug(f"Request body: {json.dumps(payload)}", extra={'user_id': user_id or 'unknown'})
            
            response = self.session.post(url, json=payload)
            
            logger.debug(f"Response status: {response.status_code}", extra={'user_id': user_id or 'unknown'})
            if response.status_code == 200:
                logger.debug(f"Response body: {response.text}", extra={'user_id': user_id or 'unknown'})
            
            if response.status_code == 200:
                data = response.json()
                logger.info(
                    f"Retrieved calendar filters: {len(data.get('TrainerFilters', []))} trainers, "
                    f"{len(data.get('CategoryFilters', []))} categories, "
                    f"{len(data.get('ZoneFilters', []))} zones, "
                    f"{len(data.get('TimeTableFilters', []))} timetables",
                    extra={'user_id': user_id or 'unknown'}
                )
                return data
            else:
                logger.error(f"Failed to get calendar filters: {response.status_code} - {response.text[:500]}", 
                            extra={'user_id': user_id or 'unknown'})
                return {}
        except Exception as e:
            logger.error(f"Error getting calendar filters: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return {}
    
    def get_classes_by_filter(self, user_filter: 'UserFilter' = None, user_id: int = None) -> List[Dict]:
        """
        Get available classes filtered by user preferences.
        
        Applies filters:
        - club_id: filter by gym/club
        - zone_id: filter by gym zone
        - timetable_id: filter by class type
        - trainer_id: filter by trainer (optional)
        - time_from, time_to: filter by time range (optional)
        """
        if not user_filter:
            # No filter provided, return all available classes
            return self.get_available_classes(user_id=user_id)
        
        try:
            # Get all available classes for the specific club in the filter
            all_classes = self.get_available_classes(user_id=user_id, club_id=user_filter.club_id, timetable_id=user_filter.timetable_id, club_name=user_filter.club_name)
            
            if not all_classes:
                logger.info(f"No classes available", extra={'user_id': user_id or 'unknown'})
                return []
            
            filtered_classes = all_classes
            
            # Filter by zone (gym)
            if user_filter.zone_id:
                # Note: API doesn't return zone_id, so we filter by zone info
                # This is a limitation - we may need to get zone info from get_calendar_filters
                logger.debug(f"Filtering by zone_id: {user_filter.zone_id}", extra={'user_id': user_id or 'unknown'})
                # For now, we'll skip zone filtering as available_classes doesn't have zone_id
                # This should be addressed by modifying get_available_classes to include zone_id
            
            # Filter by timetable_id (class type) - already applied in get_available_classes
            if user_filter.timetable_id:
                logger.debug(f"Timetable_id {user_filter.timetable_id} applied in get_available_classes", extra={'user_id': user_id or 'unknown'})
            
            # Filter by trainer
            if user_filter.trainer_id and user_filter.trainer_name:
                before_count = len(filtered_classes)
                filtered_classes = [c for c in filtered_classes if c.get('trainer_name', '').upper() == user_filter.trainer_name.upper()]
                logger.debug(f"Filtered by trainer {user_filter.trainer_name}: {before_count} -> {len(filtered_classes)}", 
                           extra={'user_id': user_id or 'unknown'})
            
            # Filter by time range
            if user_filter.time_from or user_filter.time_to:
                before_count = len(filtered_classes)
                filtered_classes = self._filter_by_time(filtered_classes, user_filter.time_from, user_filter.time_to)
                logger.debug(f"Filtered by time {user_filter.time_from}-{user_filter.time_to}: {before_count} -> {len(filtered_classes)}", 
                           extra={'user_id': user_id or 'unknown'})
            
            logger.info(f"Returned {len(filtered_classes)} classes after applying filters", 
                       extra={'user_id': user_id or 'unknown'})
            return filtered_classes
        
        except Exception as e:
            logger.error(f"Error filtering classes: {str(e)}", extra={'user_id': user_id or 'unknown'})
            return self.get_available_classes(user_id=user_id)
    
    def _filter_by_time(self, classes: List[Dict], time_from: str = None, time_to: str = None) -> List[Dict]:
        """Filter classes by time range (HH:MM format)."""
        if not time_from and not time_to:
            return classes
        
        filtered = []
        for cls in classes:
            start_time_str = cls.get('start_time', '')
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    class_time = start_time.strftime("%H:%M")
                    
                    # Check if within time range
                    if time_from and class_time < time_from:
                        continue
                    if time_to and class_time > time_to:
                        continue
                    
                    filtered.append(cls)
                except:
                    filtered.append(cls)  # If can't parse, include it
            else:
                filtered.append(cls)
        
        return filtered

