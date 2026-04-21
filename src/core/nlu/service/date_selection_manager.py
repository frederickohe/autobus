"""
Date Selection Manager for Expense Tracking
Handles generation of date selection menu and parsing of multiple user selections.
Similar to payment confirmation flow but for date-based filtering.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DateOption:
    """Represents a single date option in the selection menu"""
    
    def __init__(self, number: int, label: str, start_date: datetime, end_date: datetime):
        """
        Args:
            number: Option number (1, 2, 3, etc.)
            label: Display label (e.g., "Today", "Yesterday")
            start_date: Start of the date range (inclusive)
            end_date: End of the date range (inclusive)
        """
        self.number = number
        self.label = label
        self.start_date = start_date
        self.end_date = end_date
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "number": self.number,
            "label": self.label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'DateOption':
        """Create from dictionary"""
        return DateOption(
            number=data["number"],
            label=data["label"],
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"])
        )


class DateSelectionManager:
    """Manages date selection menu and range calculations"""
    
    @staticmethod
    def generate_date_options(reference_date: Optional[datetime] = None) -> List[DateOption]:
        """
        Generate date selection options starting from today and going backward.
        
        Format (stops at immediate previous Sunday):
        1. Today
        2. Yesterday
        3. Thursday (or previous day name)
        4. Wednesday (or previous day name)
        ... (continue until reaching immediate previous Sunday)
        N. Last Week
        N+1. Last Month
        N+2. All Time
        
        Example (if today is Tuesday Apr 16, 2026):
        1. Today (Tuesday Apr 16)
        2. Yesterday (Monday Apr 15)  
        3. Sunday (Apr 14)
        4. Last Week (Mon Mar 30 - Sun Apr 5)
        5. Last Month (Mar 1-31)
        6. All Time
        
        Args:
            reference_date: Reference date (defaults to today)
        
        Returns:
            List of DateOption objects
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Ensure we're working with dates only (set time to start of day)
        today = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        options = []
        option_number = 1
        
        # Add today
        options.append(DateOption(
            number=option_number,
            label="Today",
            start_date=today,
            end_date=today.replace(hour=23, minute=59, second=59)
        ))
        option_number += 1
        
        # Add previous days (backward from yesterday) until we reach the immediate previous Sunday
        current_date = today - timedelta(days=1)
        
        while True:
            day_name = current_date.strftime("%A")  # e.g., "Monday", "Tuesday"
            
            options.append(DateOption(
                number=option_number,
                label=day_name,
                start_date=current_date,
                end_date=current_date.replace(hour=23, minute=59, second=59)
            ))
            option_number += 1
            
            # Stop if we've reached Sunday (weekday 6)
            if current_date.weekday() == 6:
                break
            
            current_date -= timedelta(days=1)
        
        # Now current_date is the immediate previous Sunday
        # Add Last Week option: Monday-Sunday of the week before that
        last_week_end = current_date - timedelta(days=1)  # Saturday before previous Sunday
        last_week_start = last_week_end - timedelta(days=6)  # Monday
        
        options.append(DateOption(
            number=option_number,
            label="Last Week",
            start_date=last_week_start.replace(hour=0, minute=0, second=0),
            end_date=last_week_end.replace(hour=23, minute=59, second=59)
        ))
        option_number += 1
        
        # Add Last Month option
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        
        options.append(DateOption(
            number=option_number,
            label="Last Month",
            start_date=first_day_last_month.replace(hour=0, minute=0, second=0),
            end_date=last_day_last_month.replace(hour=23, minute=59, second=59)
        ))
        option_number += 1
        
        # Add All Time option
        very_old_date = datetime(2000, 1, 1, 0, 0, 0)
        options.append(DateOption(
            number=option_number,
            label="All Time",
            start_date=very_old_date,
            end_date=today.replace(hour=23, minute=59, second=59)
        ))
        
        return options
    
    @staticmethod
    def generate_menu_text(options: List[DateOption]) -> str:
        """
        Generate the menu text to display to user.
        
        Format:
        1. Today
        2. Yesterday
        3. Monday
        4. Sunday
        5. Last Week
        6. Last Month
        7. All Time
        """
        menu_lines = ["Here are your options for expense tracking:\n"]
        
        for option in options:
            menu_lines.append(f"{option.number}. {option.label}")
        
        menu_lines.append("\nYou can select multiple dates by entering numbers separated by spaces or commas.")
        menu_lines.append("Example: 1 2 3 means selecting all options 1, 2, and 3.")
        
        return "\n".join(menu_lines)
    
    @staticmethod
    def parse_selections(user_input: str, options: List[DateOption]) -> Tuple[List[DateOption], List[str]]:
        """
        Parse user's multiple selections from input.
        
        Supported formats:
        - "1 2 3" (space-separated)
        - "1, 2, 3" (comma-separated)
        - "1,2,3" (comma-separated with no spaces)
        - "1" (single selection)
        
        Args:
            user_input: Raw user input
            options: List of available DateOption objects
        
        Returns:
            Tuple of (selected_options, error_messages)
            If there are errors, selected_options will be empty and error_messages will explain the problem
        """
        selected_options = []
        error_messages = []
        
        if not user_input or not user_input.strip():
            error_messages.append("Please enter at least one option number.")
            return selected_options, error_messages
        
        # Parse user input - support both space and comma separators
        user_input = user_input.strip()
        # Replace commas with spaces and split
        numbers_str = user_input.replace(",", " ")
        number_strs = numbers_str.split()
        
        # Create a mapping of option numbers to options for quick lookup
        option_map = {opt.number: opt for opt in options}
        max_option = max(opt.number for opt in options) if options else 0
        
        for num_str in number_strs:
            num_str = num_str.strip()
            if not num_str:
                continue
            
            try:
                option_num = int(num_str)
                
                if option_num not in option_map:
                    error_messages.append(f"Option {option_num} is invalid. Valid options are 1 to {max_option}.")
                else:
                    selected_option = option_map[option_num]
                    # Avoid duplicates
                    if selected_option not in selected_options:
                        selected_options.append(selected_option)
            
            except ValueError:
                error_messages.append(f"'{num_str}' is not a valid number. Please enter numeric options only.")
        
        if not selected_options and not error_messages:
            error_messages.append("No valid options were selected.")
        
        return selected_options, error_messages
    
    @staticmethod
    def merge_date_ranges(selected_options: List[DateOption]) -> Tuple[datetime, datetime]:
        """
        Merge multiple selected date ranges into a single start and end date.
        
        If user selects: Today (1), Tuesday (2), Monday (3)
        Result: Monday 00:00 to Today 23:59
        
        Returns:
            Tuple of (earliest_start_date, latest_end_date)
        """
        if not selected_options:
            # Default to today
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today, today.replace(hour=23, minute=59, second=59)
        
        # Find the earliest start and latest end
        start_date = min(opt.start_date for opt in selected_options)
        end_date = max(opt.end_date for opt in selected_options)
        
        return start_date, end_date
    
    @staticmethod
    def format_selected_dates_summary(selected_options: List[DateOption]) -> str:
        """
        Format a human-readable summary of selected date ranges.
        
        Example output:
        "You selected: Today, Tuesday, Monday, and Last Week"
        """
        if not selected_options:
            return "No dates selected"
        
        labels = [opt.label for opt in selected_options]
        
        if len(labels) == 1:
            return f"You selected: {labels[0]}"
        elif len(labels) == 2:
            return f"You selected: {labels[0]} and {labels[1]}"
        else:
            all_but_last = ", ".join(labels[:-1])
            return f"You selected: {all_but_last}, and {labels[-1]}"
    
    @staticmethod
    def convert_time_period_to_options(time_period: str, reference_date: Optional[datetime] = None) -> List[DateOption]:
        """
        Convert extracted time_period slot values to corresponding DateOption objects.
        
        This allows users to say "show my expenses for today" instead of selecting from a menu.
        
        Args:
            time_period: Time period string from NLU slot extraction. Examples:
                - "TODAY", "YESTERDAY" (uppercase codes)
                - "Monday", "Tuesday", etc. (day names)
                - "WEEK_LAST", "MONTH_LAST", "ALL_TIME" (period codes)
                - "last week", "last month", "all time" (natural language)
            reference_date: Reference date (defaults to today)
        
        Returns:
            List of DateOption objects matching the time period
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        if not time_period:
            return []
        
        # Normalize input - handle case insensitivity and variations
        time_period_lower = time_period.strip().lower()
        time_period_upper = time_period.strip().upper()
        
        # Get all available options to match against
        all_options = DateSelectionManager.generate_date_options(reference_date)
        
        today = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # MAPPING LOGIC:
        # Direct matches for standardized codes
        if time_period_upper in ["TODAY"]:
            # Return Option 1 (Today)
            return [opt for opt in all_options if opt.number == 1]
        
        elif time_period_upper in ["YESTERDAY"]:
            # Return Option 2 (Yesterday)
            return [opt for opt in all_options if opt.number == 2]
        
        elif time_period_upper in ["WEEK_LAST", "LAST_WEEK"]:
            # Return Last Week option
            last_week_opts = [opt for opt in all_options if opt.label == "Last Week"]
            return last_week_opts
        
        elif time_period_upper in ["MONTH_LAST", "LAST_MONTH"]:
            # Return Last Month option
            last_month_opts = [opt for opt in all_options if opt.label == "Last Month"]
            return last_month_opts
        
        elif time_period_upper in ["ALL_TIME", "YEAR_1"]:
            # Return All Time option
            all_time_opts = [opt for opt in all_options if opt.label == "All Time"]
            return all_time_opts
        
        # Try to match day names (e.g., "Monday", "Tuesday", etc.)
        day_name_options = [opt for opt in all_options if opt.label not in ["Last Week", "Last Month", "All Time", "Today"]]
        for opt in day_name_options:
            if time_period_lower == opt.label.lower() or time_period.lower() == opt.label.lower():
                return [opt]
        
        # Handle week period codes (WEEK_1, WEEK_2, etc.)
        if time_period_upper in ["WEEK_1", "THIS_WEEK"]:
            # This week - typically similar to "this week" but for now return Last Week
            # (This can be refined based on requirements)
            return [opt for opt in all_options if opt.label == "Last Week"]
        
        if time_period_upper.startswith("WEEK_"):
            # Handle WEEK_2, WEEK_3, etc. - return Last Week for now
            return [opt for opt in all_options if opt.label == "Last Week"]
        
        # Handle month period codes (MONTH_1, MONTH_3, MONTH_6, etc.)
        if time_period_upper in ["MONTH_1", "THIS_MONTH"]:
            # This month - return Last Month for now
            return [opt for opt in all_options if opt.label == "Last Month"]
        
        if time_period_upper.startswith("MONTH_"):
            # Handle MONTH_3, MONTH_6, etc. - return Last Month for now
            return [opt for opt in all_options if opt.label == "Last Month"]
        
        # Natural language variations
        if "last week" in time_period_lower or "previous week" in time_period_lower:
            return [opt for opt in all_options if opt.label == "Last Week"]
        
        if "last month" in time_period_lower or "previous month" in time_period_lower:
            return [opt for opt in all_options if opt.label == "Last Month"]
        
        if "all time" in time_period_lower or "entire" in time_period_lower or "history" in time_period_lower:
            return [opt for opt in all_options if opt.label == "All Time"]
        
        if "today" in time_period_lower or "current day" in time_period_lower or "right now" in time_period_lower:
            return [opt for opt in all_options if opt.number == 1]
        
        if "yesterday" in time_period_lower or "last day" in time_period_lower:
            return [opt for opt in all_options if opt.number == 2]
        
        # No match found
        logger.warning(f"[DATE_MAPPING] Could not map time_period '{time_period}' to any option")
        return []


# Test/Example usage
if __name__ == "__main__":
    manager = DateSelectionManager()
    
    # Generate options for today (April 14, 2026 - Tuesday)
    reference = datetime(2026, 4, 14)
    options = manager.generate_date_options(reference)
    
    print("Generated options:")
    for opt in options:
        print(f"  {opt.number}. {opt.label}: {opt.start_date.date()} to {opt.end_date.date()}")
    
    print("\n" + manager.generate_menu_text(options))
    
    # Test parsing selections
    print("\n\nTest parsing:")
    test_inputs = ["1 2 3", "1, 2, 3", "1,2,3", "1", "1 5"]
    for test_input in test_inputs:
        selected, errors = manager.parse_selections(test_input, options)
        print(f"\nInput: '{test_input}'")
        if errors:
            print(f"  Errors: {errors}")
        if selected:
            print(f"  Selected: {[opt.label for opt in selected]}")
            start, end = manager.merge_date_ranges(selected)
            print(f"  Date range: {start.date()} to {end.date()}")
            print(f"  Summary: {manager.format_selected_dates_summary(selected)}")
