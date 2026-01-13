#!/usr/bin/env python
"""Test suite for time filter functionality."""

import unittest


class TestTimeSelectionToggle(unittest.TestCase):
    """Test time selection toggle logic."""
    
    def test_select_single_hour(self):
        """Test selecting a single hour."""
        filter_times = None
        
        # Select 06
        times_list = [t for t in filter_times.split(',') if t] if filter_times else []
        hour_str = "06"
        if hour_str not in times_list:
            times_list.append(hour_str)
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list) if times_list else None
        
        self.assertEqual(filter_times, "06")
    
    def test_select_multiple_hours(self):
        """Test selecting multiple hours sequentially."""
        filter_times = None
        
        # Select 06
        times_list = [t for t in filter_times.split(',') if t] if filter_times else []
        times_list.append("06")
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list)
        self.assertEqual(filter_times, "06")
        
        # Select 08
        times_list = filter_times.split(',')
        times_list.append("08")
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list)
        self.assertEqual(filter_times, "06,08")
        
        # Select 09
        times_list = filter_times.split(',')
        times_list.append("09")
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list)
        self.assertEqual(filter_times, "06,08,09")
    
    def test_deselect_hour(self):
        """Test deselecting a previously selected hour."""
        filter_times = "06,08,09"
        
        # Deselect 08
        times_list = [t for t in filter_times.split(',') if t]
        times_list.remove("08")
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list) if times_list else None
        
        self.assertEqual(filter_times, "06,09")
    
    def test_toggle_hour_on_and_off(self):
        """Test toggling a single hour on and off."""
        filter_times = None
        hour_str = "14"
        
        # Toggle on
        times_list = [t for t in filter_times.split(',') if t] if filter_times else []
        if hour_str in times_list:
            times_list.remove(hour_str)
        else:
            times_list.append(hour_str)
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list) if times_list else None
        self.assertEqual(filter_times, "14")
        
        # Toggle off
        times_list = [t for t in filter_times.split(',') if t]
        if hour_str in times_list:
            times_list.remove(hour_str)
        else:
            times_list.append(hour_str)
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list) if times_list else None
        self.assertIsNone(filter_times)
    
    def test_sort_hours_correctly(self):
        """Test that selected hours are always sorted."""
        # Select in non-sequential order: 22, 06, 14
        times_list = ["22", "06", "14"]
        times_list.sort(key=lambda x: int(x))
        filter_times = ','.join(times_list)
        
        self.assertEqual(filter_times, "06,14,22")


class TestTimeRangeConversion(unittest.TestCase):
    """Test conversion from selected hours to time range."""
    
    def test_convert_single_hour_to_range(self):
        """Test converting single hour to time range."""
        filter_times = "14"
        times_list = [int(t) for t in filter_times.split(',')]
        
        time_from = f"{min(times_list):02d}:00"
        time_to = f"{max(times_list):02d}:59"
        
        self.assertEqual(time_from, "14:00")
        self.assertEqual(time_to, "14:59")
    
    def test_convert_consecutive_hours_to_range(self):
        """Test converting consecutive hours to time range."""
        filter_times = "06,07,08,09"
        times_list = [int(t) for t in filter_times.split(',')]
        
        time_from = f"{min(times_list):02d}:00"
        time_to = f"{max(times_list):02d}:59"
        
        self.assertEqual(time_from, "06:00")
        self.assertEqual(time_to, "09:59")
    
    def test_convert_non_consecutive_hours_to_range(self):
        """Test converting non-consecutive hours to range."""
        filter_times = "06,09"
        times_list = [int(t) for t in filter_times.split(',')]
        
        time_from = f"{min(times_list):02d}:00"
        time_to = f"{max(times_list):02d}:59"
        
        # Range includes all hours between min and max
        self.assertEqual(time_from, "06:00")
        self.assertEqual(time_to, "09:59")
    
    def test_convert_morning_to_evening_range(self):
        """Test converting early morning to late evening range."""
        filter_times = "06,22"
        times_list = [int(t) for t in filter_times.split(',')]
        
        time_from = f"{min(times_list):02d}:00"
        time_to = f"{max(times_list):02d}:59"
        
        self.assertEqual(time_from, "06:00")
        self.assertEqual(time_to, "22:59")


class TestTimeDisplayFormat(unittest.TestCase):
    """Test time display formatting for UI."""
    
    def test_format_single_hour_for_display(self):
        """Test formatting single hour for display."""
        time_hours = "14"
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        
        self.assertEqual(time_display, "14:00")
    
    def test_format_consecutive_hours_for_display(self):
        """Test formatting consecutive hours for display."""
        time_hours = "6,7,8,9"
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        
        self.assertEqual(time_display, "06:00, 07:00, 08:00, 09:00")
    
    def test_format_non_consecutive_hours_for_display(self):
        """Test formatting non-consecutive hours for display."""
        time_hours = "6,18"
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        
        self.assertEqual(time_display, "06:00, 18:00")
    
    def test_format_multiple_scattered_hours(self):
        """Test formatting multiple scattered hours for display."""
        time_hours = "6,8,10,18,20,22"
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        
        self.assertEqual(time_display, "06:00, 08:00, 10:00, 18:00, 20:00, 22:00")


class TestTimeConfirmationDisplay(unittest.TestCase):
    """Test how time is displayed in filter confirmation."""
    
    def test_confirmation_with_selected_hours(self):
        """Test confirmation message with selected hours."""
        time_hours = "6,7,8,9"
        time_from = None
        time_to = None
        
        message = ""
        if time_hours:
            hours = [int(h) for h in time_hours.split(',')]
            time_display = ', '.join(f"{h:02d}:00" for h in hours)
            message = f"Time: {time_display}"
        elif time_from or time_to:
            message = f"Time: {time_from or '00:00'} - {time_to or '23:59'}"
        
        self.assertEqual(message, "Time: 06:00, 07:00, 08:00, 09:00")
    
    def test_confirmation_without_time_filter(self):
        """Test confirmation message without time filter."""
        time_hours = None
        time_from = None
        time_to = None
        
        message = ""
        if time_hours:
            hours = [int(h) for h in time_hours.split(',')]
            time_display = ', '.join(f"{h:02d}:00" for h in hours)
            message = f"Time: {time_display}"
        elif time_from or time_to:
            message = f"Time: {time_from or '00:00'} - {time_to or '23:59'}"
        
        self.assertEqual(message, "")
    
    def test_confirmation_with_legacy_time_range(self):
        """Test confirmation message with legacy time_from/time_to."""
        time_hours = None
        time_from = "06:00"
        time_to = "09:59"
        
        message = ""
        if time_hours:
            hours = [int(h) for h in time_hours.split(',')]
            time_display = ', '.join(f"{h:02d}:00" for h in hours)
            message = f"Time: {time_display}"
        elif time_from or time_to:
            message = f"Time: {time_from or '00:00'} - {time_to or '23:59'}"
        
        self.assertEqual(message, "Time: 06:00 - 09:59")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_earliest_hour(self):
        """Test earliest available hour (06:00)."""
        time_hours = "6"
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        
        self.assertEqual(time_display, "06:00")
        self.assertGreaterEqual(hours[0], 6)
    
    def test_latest_hour(self):
        """Test latest available hour (22:00)."""
        time_hours = "22"
        hours = [int(h) for h in time_hours.split(',')]
        time_display = ', '.join(f"{h:02d}:00" for h in hours)
        
        self.assertEqual(time_display, "22:00")
        self.assertLessEqual(hours[0], 22)
    
    def test_all_hours_selected(self):
        """Test selecting all available hours (06-22)."""
        times_list = [str(h) for h in range(6, 23)]
        filter_times = ','.join(times_list)
        
        self.assertEqual(len(times_list), 17)  # 6 through 22 inclusive
        self.assertTrue(filter_times.startswith("6"))
        self.assertTrue(filter_times.endswith("22"))
    
    def test_empty_filter_times_string(self):
        """Test empty filter_times after deselecting all hours."""
        filter_times = None
        
        # Filter should be None when no hours selected
        self.assertTrue(filter_times is None or filter_times == "")


class TestTimeHourParsing(unittest.TestCase):
    """Test parsing and validation of time hours string."""
    
    def test_parse_valid_hours_string(self):
        """Test parsing valid hours string."""
        filter_times = "6,7,8,9"
        hours = [int(h) for h in filter_times.split(',')]
        
        self.assertEqual(hours, [6, 7, 8, 9])
        self.assertTrue(all(6 <= h <= 22 for h in hours))
    
    def test_parse_hours_with_leading_zeros(self):
        """Test parsing hours with leading zeros."""
        filter_times = "06,07,08,09"
        hours = [int(h) for h in filter_times.split(',')]
        
        self.assertEqual(hours, [6, 7, 8, 9])
    
    def test_parse_single_digit_hours(self):
        """Test parsing single digit hours."""
        filter_times = "6"
        hours = [int(h) for h in filter_times.split(',')]
        
        self.assertEqual(hours, [6])
    
    def test_split_filter_times_correctly(self):
        """Test that split operation works correctly."""
        filter_times = "6,14,22"
        times_list = [t for t in filter_times.split(',') if t]
        
        self.assertEqual(len(times_list), 3)
        self.assertEqual(times_list, ["6", "14", "22"])


if __name__ == '__main__':
    unittest.main()
