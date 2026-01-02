"""
Smart Scheduling Engine for Day Planner

This module provides intelligent task scheduling that considers:
- Task priority (high > medium > low)
- Due dates (most urgent first)
- Task duration (estimated_duration field)
- Category balance (distribute different types of tasks)
- Rest blocks between tasks
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class SmartScheduler:
    """
    Intelligent task scheduler that creates optimized daily schedules
    """
    
    # Default settings
    DEFAULT_TASK_DURATION = 45  # minutes
    REST_BLOCK_DURATION = 10    # minutes between tasks
    MIN_TASK_DURATION = 15      # minimum task duration
    MAX_TASK_DURATION = 120     # maximum task duration (2 hours)
    
    # Priority weights for scoring
    PRIORITY_WEIGHTS = {
        'high': 100,
        'medium': 50,
        'low': 25
    }
    
    def __init__(self, start_time_minutes: int, end_time_minutes: int, current_date: date):
        """
        Initialize scheduler with time window
        
        Args:
            start_time_minutes: Start time in minutes from midnight (e.g., 540 for 9:00 AM)
            end_time_minutes: End time in minutes from midnight (e.g., 1020 for 5:00 PM)
            current_date: The date for which scheduling is being done
        """
        self.start_time = start_time_minutes
        self.end_time = end_time_minutes
        self.current_date = current_date
        self.total_available_time = end_time_minutes - start_time_minutes
        
    def calculate_task_score(self, task: Dict, category_usage: Dict[str, int]) -> float:
        """
        Calculate priority score for a task based on multiple factors
        
        Higher score = higher priority
        
        Factors considered:
        1. Priority level (high=100, medium=50, low=25)
        2. Due date urgency (closer due date = higher score)
        3. Category balance (less used categories get bonus)
        
        Args:
            task: Task dictionary with fields (priority, due_date, category, etc.)
            category_usage: Dictionary tracking how many tasks scheduled per category
            
        Returns:
            float: Priority score (higher = more important)
        """
        score = 0.0
        
        # 1. Base priority score
        priority = task.get('priority', 'medium')
        score += self.PRIORITY_WEIGHTS.get(priority, 50)
        
        # 2. Due date urgency (add up to 200 points based on urgency)
        due_date = task.get('due_date')
        if due_date:
            if isinstance(due_date, str):
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                except:
                    due_date = None
            
            if due_date:
                days_until_due = (due_date - self.current_date).days
                
                if days_until_due < 0:
                    # Overdue - highest priority
                    score += 200
                elif days_until_due == 0:
                    # Due today - very high priority
                    score += 150
                elif days_until_due == 1:
                    # Due tomorrow - high priority
                    score += 100
                elif days_until_due <= 3:
                    # Due within 3 days - elevated priority
                    score += 75
                elif days_until_due <= 7:
                    # Due within a week - moderate priority
                    score += 50
                else:
                    # Due later - some priority
                    score += max(0, 25 - (days_until_due // 7) * 5)
        
        # 3. Category balance (reduce score for overused categories)
        category_name = task.get('category_name', 'Uncategorized')
        category_count = category_usage.get(category_name, 0)
        
        # Penalize overused categories to encourage variety
        if category_count > 0:
            score -= category_count * 15  # -15 points per task already scheduled in this category
        
        return score
    
    def get_task_duration(self, task: Dict) -> int:
        """
        Get the duration for a task, with fallback to default
        
        Args:
            task: Task dictionary
            
        Returns:
            int: Duration in minutes
        """
        duration = task.get('estimated_duration') or task.get('duration')
        
        if duration:
            # Clamp duration to reasonable bounds
            duration = max(self.MIN_TASK_DURATION, min(self.MAX_TASK_DURATION, duration))
        else:
            duration = self.DEFAULT_TASK_DURATION
            
        return duration
    
    def schedule_tasks(self, tasks: List[Dict]) -> Tuple[List[Dict], Dict[str, any]]:
        """
        Create an optimized schedule from a list of tasks
        
        Args:
            tasks: List of task dictionaries with fields:
                   - id, title, priority, due_date, category_name, estimated_duration
        
        Returns:
            Tuple of:
                - List of scheduled event dictionaries
                - Statistics dictionary
        """
        if not tasks:
            return [], {
                'scheduled_count': 0,
                'total_work_time': 0,
                'total_rest_time': 0,
                'unscheduled_count': 0,
                'category_distribution': {}
            }
        
        # Track category usage for balancing
        category_usage = defaultdict(int)
        
        # Schedule tasks into time slots
        scheduled_events = []
        current_time = self.start_time
        scheduled_count = 0
        total_work_time = 0
        total_rest_time = 0
        category_distribution = defaultdict(int)
        remaining_tasks = list(tasks)  # Copy the list
        
        while remaining_tasks and current_time < self.end_time:
            # Score all remaining tasks
            scored_tasks = []
            for task in remaining_tasks:
                score = self.calculate_task_score(task, category_usage)
                scored_tasks.append((score, task))
            
            # Sort by score (descending) - highest priority first
            scored_tasks.sort(key=lambda x: x[0], reverse=True)
            
            # Try to schedule the highest priority task that fits
            scheduled_this_round = False
            for score, task in scored_tasks:
                duration = self.get_task_duration(task)
                
                # Check if we have enough time for this task
                if current_time + duration <= self.end_time:
                    # Create scheduled event
                    event = {
                        'id': f"auto_{task['id']}_{scheduled_count}",
                        'title': task['title'],
                        'startMin': current_time,
                        'endMin': current_time + duration,
                        'logged': False,
                        'planNames': task.get('plan_names', []),
                        'taskId': task['id'],
                        'category': task.get('category_name'),
                        'priority': task.get('priority', 'medium'),
                        'isCalendarEvent': False
                    }
                    
                    scheduled_events.append(event)
                    
                    # Update tracking variables
                    category_name = task.get('category_name', 'Uncategorized')
                    category_usage[category_name] += 1
                    category_distribution[category_name] += 1
                    scheduled_count += 1
                    total_work_time += duration
                    current_time += duration
                    
                    # Remove scheduled task from remaining tasks
                    remaining_tasks.remove(task)
                    
                    # Add rest block after task (if there's time and more tasks)
                    if remaining_tasks and current_time + self.REST_BLOCK_DURATION <= self.end_time:
                        current_time += self.REST_BLOCK_DURATION
                        total_rest_time += self.REST_BLOCK_DURATION
                    
                    scheduled_this_round = True
                    break
            
            # If we couldn't schedule any task, break to avoid infinite loop
            if not scheduled_this_round:
                break
        
        # Compile statistics
        stats = {
            'scheduled_count': scheduled_count,
            'total_work_time': total_work_time,
            'total_rest_time': total_rest_time,
            'unscheduled_count': len(remaining_tasks),
            'category_distribution': dict(category_distribution),
            'end_time': current_time - (self.REST_BLOCK_DURATION if total_rest_time > 0 and current_time > self.start_time else 0)
        }
        
        return scheduled_events, stats
    
    @staticmethod
    def format_time(minutes: int) -> str:
        """Convert minutes from midnight to HH:MM format"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in a human-readable way"""
        if minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins > 0:
                return f"{hours}h {mins}m"
            else:
                return f"{hours}h"
