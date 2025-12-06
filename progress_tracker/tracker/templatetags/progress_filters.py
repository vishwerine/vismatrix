# tracker/templatetags/progress_filters.py

"""
Custom template filters for progress tracking and statistics.
Place this file in: tracker/templatetags/progress_filters.py
"""

from django import template
from django.db.models import Sum, Count, Q

register = template.Library()


# ============================================================================
# AGGREGATION FILTERS - Sum values from list of progress objects
# ============================================================================

@register.filter
def sum_total_tasks(progress_list):
    """
    Sum total tasks from a list of progress dictionaries.
    
    Usage: {{ progress_data|sum_total_tasks }}
    
    Args:
        progress_list: List of dictionaries with 'total_tasks' key
        
    Returns:
        int: Sum of all total_tasks
    """
    if not progress_list:
        return 0
    
    try:
        total = 0
        for item in progress_list:
            if isinstance(item, dict):
                total += item.get('total_tasks', 0)
            else:
                total += getattr(item, 'total_tasks', 0)
        return total
    except (TypeError, AttributeError):
        return 0


@register.filter
def sum_completed_tasks(progress_list):
    """
    Sum completed tasks from a list of progress dictionaries.
    
    Usage: {{ progress_data|sum_completed_tasks }}
    
    Args:
        progress_list: List of dictionaries with 'completed_tasks' key
        
    Returns:
        int: Sum of all completed_tasks
    """
    if not progress_list:
        return 0
    
    try:
        total = 0
        for item in progress_list:
            if isinstance(item, dict):
                total += item.get('completed_tasks', 0)
            else:
                total += getattr(item, 'completed_tasks', 0)
        return total
    except (TypeError, AttributeError):
        return 0


@register.filter
def sum_total_time_logged(progress_list):
    """
    Sum total time logged from a list of progress dictionaries.
    
    Usage: {{ progress_data|sum_total_time_logged }}
    
    Args:
        progress_list: List of dictionaries with 'total_time_logged' key
        
    Returns:
        int or float: Sum of all total_time_logged (in hours)
    """
    if not progress_list:
        return 0
    
    try:
        total = 0
        for item in progress_list:
            if isinstance(item, dict):
                total += item.get('total_time_logged', 0)
            else:
                total += getattr(item, 'total_time_logged', 0)
        return round(total, 1)
    except (TypeError, AttributeError):
        return 0


@register.filter
def sum_pending_tasks(progress_list):
    """
    Sum pending (incomplete) tasks from a list of progress dictionaries.
    
    Usage: {{ progress_data|sum_pending_tasks }}
    
    Args:
        progress_list: List of dictionaries with 'total_tasks' and 'completed_tasks'
        
    Returns:
        int: Sum of all pending tasks (total - completed)
    """
    if not progress_list:
        return 0
    
    try:
        total_tasks = 0
        completed_tasks = 0
        
        for item in progress_list:
            if isinstance(item, dict):
                total_tasks += item.get('total_tasks', 0)
                completed_tasks += item.get('completed_tasks', 0)
            else:
                total_tasks += getattr(item, 'total_tasks', 0)
                completed_tasks += getattr(item, 'completed_tasks', 0)
        
        return max(0, total_tasks - completed_tasks)
    except (TypeError, AttributeError):
        return 0


# ============================================================================
# PERCENTAGE AND CALCULATION FILTERS
# ============================================================================

@register.filter
def calculate_completion_percentage(progress_list):
    """
    Calculate overall completion percentage from a list of progress objects.
    
    Usage: {{ progress_data|calculate_completion_percentage }}%
    
    Args:
        progress_list: List of dictionaries with 'total_tasks' and 'completed_tasks'
        
    Returns:
        float: Completion percentage (0-100), rounded to 1 decimal place
    """
    if not progress_list:
        return 0
    
    try:
        total_tasks = 0
        completed_tasks = 0
        
        for item in progress_list:
            if isinstance(item, dict):
                total_tasks += item.get('total_tasks', 0)
                completed_tasks += item.get('completed_tasks', 0)
            else:
                total_tasks += getattr(item, 'total_tasks', 0)
                completed_tasks += getattr(item, 'completed_tasks', 0)
        
        if total_tasks == 0:
            return 0
        
        percentage = (completed_tasks / total_tasks) * 100
        return round(percentage, 1)
    except (TypeError, AttributeError, ZeroDivisionError):
        return 0


@register.filter
def calculate_average_completion(progress_list):
    """
    Calculate average completion percentage across all items.
    
    Usage: {{ progress_data|calculate_average_completion }}%
    
    Args:
        progress_list: List of dictionaries with completion percentages
        
    Returns:
        float: Average completion percentage, rounded to 1 decimal place
    """
    if not progress_list:
        return 0
    
    try:
        percentages = []
        
        for item in progress_list:
            if isinstance(item, dict):
                total = item.get('total_tasks', 0)
                completed = item.get('completed_tasks', 0)
            else:
                total = getattr(item, 'total_tasks', 0)
                completed = getattr(item, 'completed_tasks', 0)
            
            if total > 0:
                pct = (completed / total) * 100
                percentages.append(pct)
        
        if not percentages:
            return 0
        
        average = sum(percentages) / len(percentages)
        return round(average, 1)
    except (TypeError, AttributeError, ZeroDivisionError):
        return 0


@register.filter
def calculate_productivity_score(item):
    """
    Calculate a productivity score based on tasks and time logged.
    
    Usage: {{ item|calculate_productivity_score }}
    
    Formula: (completed_tasks * 10) + (total_time_logged * 5)
    
    Args:
        item: Dictionary or object with 'completed_tasks' and 'total_time_logged'
        
    Returns:
        int: Productivity score
    """
    try:
        if isinstance(item, dict):
            completed = item.get('completed_tasks', 0)
            time_logged = item.get('total_time_logged', 0)
        else:
            completed = getattr(item, 'completed_tasks', 0)
            time_logged = getattr(item, 'total_time_logged', 0)
        
        # Score = (completed tasks * 10) + (hours logged * 5)
        score = (completed * 10) + (time_logged * 5)
        return int(score)
    except (TypeError, AttributeError):
        return 0


# ============================================================================
# SINGLE VALUE EXTRACTION FILTERS
# ============================================================================

@register.filter
def get_single_value(item, key):
    """
    Get a specific value from a dictionary or object by key.
    
    Usage: {{ item|get_single_value:"total_tasks" }}
    
    Args:
        item: Dictionary or object
        key: Key or attribute name to retrieve
        
    Returns:
        Value at the key, or 0 if not found
    """
    try:
        if isinstance(item, dict):
            return item.get(key, 0)
        else:
            return getattr(item, key, 0)
    except (TypeError, AttributeError):
        return 0


@register.filter
def get_percentage(item, key):
    """
    Get a specific percentage value from a dictionary, formatted with % sign.
    
    Usage: {{ item|get_percentage:"completion_percentage" }}
    
    Args:
        item: Dictionary or object
        key: Key or attribute name containing percentage value
        
    Returns:
        String formatted as "XX.X%"
    """
    try:
        if isinstance(item, dict):
            value = item.get(key, 0)
        else:
            value = getattr(item, key, 0)
        return f"{value}%"
    except (TypeError, AttributeError):
        return "0%"


# ============================================================================
# LIST STATISTICS FILTERS
# ============================================================================

@register.filter
def count_items(progress_list):
    """
    Count the number of items in a list.
    
    Usage: {{ progress_data|count_items }}
    
    Args:
        progress_list: Any iterable
        
    Returns:
        int: Number of items
    """
    try:
        return len(progress_list) if progress_list else 0
    except TypeError:
        return 0


@register.filter
def get_highest_completion(progress_list):
    """
    Get the highest completion percentage from a list of progress objects.
    
    Usage: {{ progress_data|get_highest_completion }}%
    
    Args:
        progress_list: List of dictionaries with progress data
        
    Returns:
        float: Highest completion percentage
    """
    if not progress_list:
        return 0
    
    try:
        max_percentage = 0
        
        for item in progress_list:
            if isinstance(item, dict):
                total = item.get('total_tasks', 0)
                completed = item.get('completed_tasks', 0)
            else:
                total = getattr(item, 'total_tasks', 0)
                completed = getattr(item, 'completed_tasks', 0)
            
            if total > 0:
                pct = (completed / total) * 100
                max_percentage = max(max_percentage, pct)
        
        return round(max_percentage, 1)
    except (TypeError, AttributeError):
        return 0


@register.filter
def get_lowest_completion(progress_list):
    """
    Get the lowest completion percentage from a list of progress objects.
    
    Usage: {{ progress_data|get_lowest_completion }}%
    
    Args:
        progress_list: List of dictionaries with progress data
        
    Returns:
        float: Lowest completion percentage
    """
    if not progress_list:
        return 0
    
    try:
        min_percentage = 100
        found_any = False
        
        for item in progress_list:
            if isinstance(item, dict):
                total = item.get('total_tasks', 0)
                completed = item.get('completed_tasks', 0)
            else:
                total = getattr(item, 'total_tasks', 0)
                completed = getattr(item, 'completed_tasks', 0)
            
            if total > 0:
                pct = (completed / total) * 100
                min_percentage = min(min_percentage, pct)
                found_any = True
        
        return round(min_percentage, 1) if found_any else 0
    except (TypeError, AttributeError):
        return 0


@register.filter
def get_total_count(progress_list, field_name):
    """
    Get total count of a specific field from all items.
    
    Usage: {{ progress_data|get_total_count:"total_tasks" }}
    
    Args:
        progress_list: List of dictionaries or objects
        field_name: Name of the field to sum
        
    Returns:
        int or float: Total sum of the field
    """
    if not progress_list:
        return 0
    
    try:
        total = 0
        for item in progress_list:
            if isinstance(item, dict):
                total += item.get(field_name, 0)
            else:
                total += getattr(item, field_name, 0)
        return total
    except (TypeError, AttributeError):
        return 0


# ============================================================================
# FORMATTING FILTERS
# ============================================================================

@register.filter
def format_time(hours):
    """
    Format hours into human-readable time format (h, d, w).
    
    Usage: {{ total_time_logged|format_time }}
    
    Args:
        hours: Number of hours
        
    Returns:
        String formatted as "Xh", "Xd", "Xw"
    """
    try:
        hours = float(hours)
        
        if hours < 1:
            return f"{int(hours * 60)}m"
        elif hours < 24:
            return f"{hours:.1f}h"
        elif hours < 168:  # 168 hours = 7 days
            days = hours / 24
            return f"{days:.1f}d"
        else:
            weeks = hours / 168
            return f"{weeks:.1f}w"
    except (TypeError, ValueError):
        return "0h"


@register.filter
def format_number(value):
    """
    Format number with thousand separators.
    
    Usage: {{ total_tasks|format_number }}
    
    Args:
        value: Number to format
        
    Returns:
        String with thousand separators
    """
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


# ============================================================================
# COMPARISON FILTERS
# ============================================================================

@register.filter
def is_high_productivity(item, threshold=80):
    """
    Check if productivity is high (completion percentage >= threshold).
    
    Usage: {% if item|is_high_productivity %}High{% endif %}
    
    Args:
        item: Dictionary or object with progress data
        threshold: Minimum completion percentage (default: 80)
        
    Returns:
        bool: True if completion >= threshold
    """
    try:
        if isinstance(item, dict):
            total = item.get('total_tasks', 0)
            completed = item.get('completed_tasks', 0)
        else:
            total = getattr(item, 'total_tasks', 0)
            completed = getattr(item, 'completed_tasks', 0)
        
        if total == 0:
            return False
        
        percentage = (completed / total) * 100
        return percentage >= threshold
    except (TypeError, AttributeError):
        return False


@register.filter
def compare_progress(item1, item2):
    """
    Compare two progress items and return the difference in completion percentage.
    
    Usage: {{ item1|compare_progress:item2 }}
    
    Args:
        item1: First progress dictionary/object
        item2: Second progress dictionary/object
        
    Returns:
        float: Difference in completion percentage (item1 - item2)
    """
    try:
        # Calculate item1 completion
        if isinstance(item1, dict):
            total1 = item1.get('total_tasks', 0)
            completed1 = item1.get('completed_tasks', 0)
        else:
            total1 = getattr(item1, 'total_tasks', 0)
            completed1 = getattr(item1, 'completed_tasks', 0)
        
        pct1 = (completed1 / total1 * 100) if total1 > 0 else 0
        
        # Calculate item2 completion
        if isinstance(item2, dict):
            total2 = item2.get('total_tasks', 0)
            completed2 = item2.get('completed_tasks', 0)
        else:
            total2 = getattr(item2, 'total_tasks', 0)
            completed2 = getattr(item2, 'completed_tasks', 0)
        
        pct2 = (completed2 / total2 * 100) if total2 > 0 else 0
        
        return round(pct1 - pct2, 1)
    except (TypeError, AttributeError, ZeroDivisionError):
        return 0