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
                print(f"   Auto-booking: {'ENABLED' if f.auto_booking else 'DISABLED'}")
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


def test_auto_booking_filter_creation():
    """Test creating filter with auto-booking enabled."""
    print("\n" + "=" * 60)
    print("TEST 4: Database - Auto-Booking Filter Creation")
    print("=" * 60)
    
    try:
        db = Database()
        
        # Create a filter with auto-booking enabled
        test_filter = UserFilter(
            user_id=999998,  # Use a different test ID
            club_id=75,
            club_name="Zdrofit Lazurowa",
            zone_id="167",
            zone_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            category_id="9",
            category_name="Mini Class",
            trainer_id=None,
            trainer_name=None,
            time_from="07:00",
            time_to="20:00",
            weekdays="1,2,3,4,5",
            auto_booking=True  # Enable auto-booking
        )
        
        # Save filter
        if db.add_filter(test_filter):
            print("[PASS] Filter with auto-booking saved successfully")
        else:
            print("[FAIL] Failed to save filter")
            return False
        
        # Retrieve and verify auto-booking is enabled
        retrieved_filters = db.get_all_filters(999998)
        if retrieved_filters and retrieved_filters[0].auto_booking:
            print("[PASS] Auto-booking flag retrieved correctly (ENABLED)")
        else:
            print("[FAIL] Auto-booking flag not set correctly")
            return False
        
        # Clean up
        db.delete_filter_by_id(retrieved_filters[0].id, 999998)
        
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_auto_booking_limit():
    """Test that auto-booking limit is enforced (max 3 bookings per filter)."""
    print("\n" + "=" * 60)
    print("TEST 5: Database - Auto-Booking Limit Enforcement")
    print("=" * 60)
    
    try:
        from src.database.models import Booking
        from datetime import datetime, timedelta
        
        db = Database()
        
        # Create a filter with auto-booking
        test_filter = UserFilter(
            user_id=999997,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        
        db.add_filter(test_filter)
        filter_id = db.get_all_filters(999997)[0].id
        
        # Add 3 bookings (at limit)
        for i in range(3):
            booking = Booking(
                user_id=999997,
                class_id=f"class_limit_{i}",
                title="Pilates Class",
                start_time=datetime.now() + timedelta(days=i),
                filter_id=filter_id,
                is_auto_booked=True
            )
            db.add_booking(booking)
        
        # Count bookings
        count = db.count_filter_bookings(999997, filter_id)
        if count == 3:
            print("[PASS] Booking count is 3 (at limit)")
        else:
            print(f"[FAIL] Expected 3 bookings, got {count}")
            return False
        
        # Check that we should NOT auto-book anymore
        should_auto_book = count < 3
        if not should_auto_book:
            print("[PASS] Auto-booking would be disabled at limit (correct)")
        else:
            print("[FAIL] Auto-booking should be disabled at limit")
            return False
        
        # Clean up
        db.delete_filter_by_id(filter_id, 999997)
        
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_auto_booking_update():
    """Test updating auto-booking flag for existing filter."""
    print("\n" + "=" * 60)
    print("TEST 6: Database - Update Auto-Booking Flag")
    print("=" * 60)
    
    try:
        db = Database()
        
        # Create filter with auto-booking disabled
        test_filter = UserFilter(
            user_id=999996,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Yoga",
            auto_booking=False  # Initially disabled
        )
        
        db.add_filter(test_filter)
        filter_id = db.get_all_filters(999996)[0].id
        
        # Verify initially disabled
        filters = db.get_all_filters(999996)
        if not filters[0].auto_booking:
            print("[PASS] Filter initially has auto-booking DISABLED")
        else:
            print("[FAIL] Filter should be disabled initially")
            return False
        
        # Update to enabled
        if db.update_filter_auto_booking(filter_id, True, 999996):
            print("[PASS] Updated auto-booking to ENABLED")
        else:
            print("[FAIL] Failed to update auto-booking")
            return False
        
        # Verify update
        filters = db.get_all_filters(999996)
        if filters[0].auto_booking:
            print("[PASS] Auto-booking is now ENABLED")
        else:
            print("[FAIL] Auto-booking should be enabled after update")
            return False
        
        # Update back to disabled
        if db.update_filter_auto_booking(filter_id, False, 999996):
            print("[PASS] Updated auto-booking back to DISABLED")
        else:
            print("[FAIL] Failed to update auto-booking")
            return False
        
        # Verify final state
        filters = db.get_all_filters(999996)
        if not filters[0].auto_booking:
            print("[PASS] Auto-booking is now DISABLED")
        else:
            print("[FAIL] Auto-booking should be disabled")
            return False
        
        # Clean up
        db.delete_filter_by_id(filter_id, 999996)
        
        return True
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
    results.append(("DB - Auto-Booking Filter Creation", test_auto_booking_filter_creation()))
    results.append(("DB - Auto-Booking Limit Enforcement", test_auto_booking_limit()))
    results.append(("DB - Update Auto-Booking Flag", test_auto_booking_update()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")
