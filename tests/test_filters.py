#!/usr/bin/env python
"""Test script for filter functionality."""

import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import UserFilter
from src.api.zdrofit_client import ZdrofitAPIClient

# Test credentials (use your own)
TEST_EMAIL = "sergeistamal@gmail.com"
TEST_PASSWORD = "your_password_here"  # Replace with actual password
TEST_USER_ID = 6181242580


def test_api_get_calendar_filters():
    """Test getting calendar filters from API."""
    print("\n" + "=" * 60)
    print("TEST 1: API - Get Calendar Filters")
    print("=" * 60)
    
    try:
        client = ZdrofitAPIClient(TEST_EMAIL, TEST_PASSWORD)
        if not client.authenticate(TEST_USER_ID):
            print("[FAIL] Failed to authenticate")
            return False
        
        print("[PASS] Authenticated successfully")
        
        # Get filters for club 75 (Lazurowa)
        filters = client.get_calendar_filters(user_id=TEST_USER_ID, club_id=75)
        
        if not filters:
            print("[FAIL] No filters returned from API")
            return False
        
        print("[PASS] Got filters from API")
        
        zones = filters.get('ZoneFilters', [])
        print(f"\nAvailable Zones ({len(zones)}):")
        for zone in zones[:3]:  # Show first 3
            print(f"   - {zone.get('Name')} (ID: {zone.get('Id')})")
        
        timetables = filters.get('TimeTableFilters', [])
        print(f"\nAvailable Timetables ({len(timetables)}):")
        for tt in timetables[:3]:  # Show first 3
            print(f"   - {tt.get('Name')} (ID: {tt.get('Id')})")
        
        trainers = filters.get('TrainerFilters', [])
        print(f"\nAvailable Trainers ({len(trainers)}):")
        for trainer in trainers[:3]:  # Show first 3
            print(f"   - {trainer.get('Name')} (ID: {trainer.get('Id')})")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_db_filter_operations():
    """Test database filter operations."""
    print("\n" + "=" * 60)
    print("TEST 2: Database - Filter Operations")
    print("=" * 60)
    
    try:
        db = Database()
        
        # Create a test filter with current model structure
        test_filter = UserFilter(
            user_id=999999,  # Use a test ID
            club_id=75,
            club_name="Zdrofit Lazurowa",
            zone_id="167",
            zone_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Full Body Workout",
            category_id="9",
            category_name="Wzmacniające",
            trainer_id=None,
            trainer_name=None,
            time_from="07:00",
            time_to="20:00",
            weekdays="1,2,3,4,5"  # Monday to Friday
        )
        
        # Save filter
        if db.add_filter(test_filter):
            print("[PASS] Filter saved successfully")
        else:
            print("[FAIL] Failed to save filter")
            return False
        
        # Retrieve all filters for user
        retrieved_filters = db.get_all_filters(999999)
        if retrieved_filters:
            print("[PASS] Filters retrieved successfully")
            for f in retrieved_filters:
                print(f"\nRetrieved Filter:")
                print(f"   Club: {f.club_name} ({f.club_id})")
                print(f"   Zone: {f.zone_name} ({f.zone_id})")
                print(f"   Timetable: {f.timetable_name} ({f.timetable_id})")
                if f.trainer_name:
                    print(f"   Trainer: {f.trainer_name} ({f.trainer_id})")
                print(f"   Time: {f.time_from} - {f.time_to}")
                if f.weekdays:
                    print(f"   Days: {f.weekdays}")
        else:
            print("[FAIL] Failed to retrieve filters")
            return False
        
        # Delete filter
        filter_id = retrieved_filters[0].id
        if db.delete_filter(filter_id):
            print("[PASS] Filter deleted successfully")
        else:
            print("[FAIL] Failed to delete filter")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_get_available_classes():
    """Test getting available classes with filters."""
    print("\n" + "=" * 60)
    print("TEST 3: API - Get Available Classes")
    print("=" * 60)
    
    try:
        client = ZdrofitAPIClient(TEST_EMAIL, TEST_PASSWORD)
        if not client.authenticate(TEST_USER_ID):
            print("[FAIL] Failed to authenticate")
            return False
        
        print("[PASS] Authenticated successfully")
        
        # Get available classes for club 75, timetable 63 (Full Body Workout)
        classes = client.get_available_classes(
            user_id=TEST_USER_ID,
            club_id=75,
            timetable_id="63",
            club_name="Zdrofit Lazurowa"
        )
        
        if isinstance(classes, list):
            print(f"[PASS] Retrieved {len(classes)} available classes")
            
            for cls in classes[:3]:  # Show first 3
                print(f"\n   {cls.get('title')}")
                print(f"      Gym: {cls.get('gym_name')}")
                print(f"      Trainer: {cls.get('trainer_name')}")
                print(f"      Time: {cls.get('start_time')}")
                print(f"      Available spots: {cls.get('available_spots')}")
            
            return True
        else:
            print("[FAIL] Invalid response format")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nFilter Functionality Test Suite")
    print("=" * 60)
    
    results = []
    
    # Note: Tests require real API credentials
    print("\nNOTE: Tests require real API credentials!")
    print(f"Current email: {TEST_EMAIL}")
    
    response = input("\nRun API tests? (y/n): ").lower()
    if response == 'y':
        if TEST_PASSWORD == "your_password_here":
            print("[FAIL] Please update TEST_PASSWORD in the script first!")
        else:
            results.append(("API - Get Calendar Filters", test_api_get_calendar_filters()))
            results.append(("API - Get Available Classes", test_get_available_classes()))
    
    # Database tests don't need credentials
    results.append(("DB - Filter Operations", test_db_filter_operations()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
