"""
Test script for Smart Scheduler

This script tests the smart scheduling algorithm with various task combinations
to ensure it properly prioritizes tasks and creates balanced schedules.
"""

from datetime import date, timedelta
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tracker', 'services'))

# Import just the scheduler module directly
from smart_scheduler import SmartScheduler


def test_basic_scheduling():
    """Test basic scheduling with simple tasks"""
    print("=" * 60)
    print("TEST 1: Basic Scheduling")
    print("=" * 60)
    
    today = date.today()
    scheduler = SmartScheduler(
        start_time_minutes=9 * 60,  # 9:00 AM
        end_time_minutes=17 * 60,   # 5:00 PM
        current_date=today
    )
    
    tasks = [
        {
            'id': 1,
            'title': 'Review Python Code',
            'priority': 'high',
            'due_date': today.isoformat(),
            'category_name': 'Programming',
            'estimated_duration': 60,
            'plan_names': []
        },
        {
            'id': 2,
            'title': 'Write Documentation',
            'priority': 'medium',
            'due_date': (today + timedelta(days=1)).isoformat(),
            'category_name': 'Documentation',
            'estimated_duration': 45,
            'plan_names': []
        },
        {
            'id': 3,
            'title': 'Team Meeting',
            'priority': 'high',
            'due_date': today.isoformat(),
            'category_name': 'Meetings',
            'estimated_duration': 30,
            'plan_names': []
        },
    ]
    
    events, stats = scheduler.schedule_tasks(tasks)
    
    print(f"\n📊 Statistics:")
    print(f"  Scheduled: {stats['scheduled_count']} tasks")
    print(f"  Work time: {scheduler.format_duration(stats['total_work_time'])}")
    print(f"  Rest time: {scheduler.format_duration(stats['total_rest_time'])}")
    print(f"  Unscheduled: {stats['unscheduled_count']} tasks")
    
    print(f"\n📅 Scheduled Events:")
    for event in events:
        print(f"  {scheduler.format_time(event['startMin'])} - {scheduler.format_time(event['endMin'])}: "
              f"{event['title']} ({event['priority']}, {event['category']})")
    
    assert stats['scheduled_count'] == 3, "Should schedule all 3 tasks"
    assert stats['total_rest_time'] == 20, "Should have 2 rest blocks (10 min each)"
    print("\n✅ Test 1 Passed!\n")


def test_priority_ordering():
    """Test that high priority and urgent tasks are scheduled first"""
    print("=" * 60)
    print("TEST 2: Priority Ordering")
    print("=" * 60)
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    scheduler = SmartScheduler(
        start_time_minutes=9 * 60,
        end_time_minutes=12 * 60,  # Limited time window
        current_date=today
    )
    
    tasks = [
        {
            'id': 1,
            'title': 'Low Priority Future Task',
            'priority': 'low',
            'due_date': next_week.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 45,
            'plan_names': []
        },
        {
            'id': 2,
            'title': 'High Priority Overdue Task',
            'priority': 'high',
            'due_date': yesterday.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 60,
            'plan_names': []
        },
        {
            'id': 3,
            'title': 'Medium Priority Today Task',
            'priority': 'medium',
            'due_date': today.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 45,
            'plan_names': []
        },
    ]
    
    events, stats = scheduler.schedule_tasks(tasks)
    
    print(f"\n📊 Statistics:")
    print(f"  Scheduled: {stats['scheduled_count']} tasks")
    
    print(f"\n📅 Scheduled Events (in order):")
    for i, event in enumerate(events):
        task = next(t for t in tasks if t['id'] == event['taskId'])
        print(f"  {i+1}. {event['title']} (Priority: {task['priority']}, Due: {task['due_date']})")
    
    # First task should be the overdue high priority one
    first_task_id = events[0]['taskId']
    first_task = next(t for t in tasks if t['id'] == first_task_id)
    
    assert first_task['id'] == 2, "Overdue high-priority task should be scheduled first"
    print("\n✅ Test 2 Passed!\n")


def test_category_balancing():
    """Test that tasks are balanced across categories"""
    print("=" * 60)
    print("TEST 3: Category Balancing")
    print("=" * 60)
    
    today = date.today()
    scheduler = SmartScheduler(
        start_time_minutes=9 * 60,
        end_time_minutes=17 * 60,
        current_date=today
    )
    
    # Many tasks in one category, fewer in another
    tasks = []
    for i in range(5):
        tasks.append({
            'id': i + 1,
            'title': f'Programming Task {i+1}',
            'priority': 'medium',
            'due_date': today.isoformat(),
            'category_name': 'Programming',
            'estimated_duration': 45,
            'plan_names': []
        })
    
    tasks.append({
        'id': 6,
        'title': 'Design Task',
        'priority': 'medium',
        'due_date': today.isoformat(),
        'category_name': 'Design',
        'estimated_duration': 45,
        'plan_names': []
    })
    
    tasks.append({
        'id': 7,
        'title': 'Meeting Task',
        'priority': 'medium',
        'due_date': today.isoformat(),
        'category_name': 'Meetings',
        'estimated_duration': 45,
        'plan_names': []
    })
    
    events, stats = scheduler.schedule_tasks(tasks)
    
    print(f"\n📊 Statistics:")
    print(f"  Scheduled: {stats['scheduled_count']} tasks")
    print(f"\n📂 Category Distribution:")
    for category, count in stats['category_distribution'].items():
        print(f"  {category}: {count} tasks")
    
    print(f"\n📅 Scheduled Events (showing category diversity):")
    for i, event in enumerate(events[:5]):  # Show first 5
        print(f"  {i+1}. {event['title']} ({event['category']})")
    
    # Check that we have at least 2 different categories in first 3 tasks
    first_three_categories = set(event['category'] for event in events[:3])
    assert len(first_three_categories) >= 2, "Should balance categories in scheduling"
    print("\n✅ Test 3 Passed!\n")


def test_rest_blocks():
    """Test that rest blocks are inserted between tasks"""
    print("=" * 60)
    print("TEST 4: Rest Blocks")
    print("=" * 60)
    
    today = date.today()
    scheduler = SmartScheduler(
        start_time_minutes=9 * 60,
        end_time_minutes=11 * 60,
        current_date=today
    )
    
    tasks = [
        {
            'id': 1,
            'title': 'Task 1',
            'priority': 'medium',
            'due_date': today.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 45,
            'plan_names': []
        },
        {
            'id': 2,
            'title': 'Task 2',
            'priority': 'medium',
            'due_date': today.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 45,
            'plan_names': []
        },
    ]
    
    events, stats = scheduler.schedule_tasks(tasks)
    
    print(f"\n📊 Statistics:")
    print(f"  Work time: {scheduler.format_duration(stats['total_work_time'])}")
    print(f"  Rest time: {scheduler.format_duration(stats['total_rest_time'])}")
    
    if len(events) >= 2:
        gap = events[1]['startMin'] - events[0]['endMin']
        print(f"\n⏱️  Gap between tasks: {gap} minutes")
        assert gap == 10, "Should have 10-minute rest block between tasks"
    
    print("\n✅ Test 4 Passed!\n")


def test_duration_handling():
    """Test that task durations are properly used"""
    print("=" * 60)
    print("TEST 5: Duration Handling")
    print("=" * 60)
    
    today = date.today()
    scheduler = SmartScheduler(
        start_time_minutes=9 * 60,
        end_time_minutes=17 * 60,
        current_date=today
    )
    
    tasks = [
        {
            'id': 1,
            'title': 'Short Task',
            'priority': 'high',
            'due_date': today.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 15,  # Minimum duration
            'plan_names': []
        },
        {
            'id': 2,
            'title': 'Long Task',
            'priority': 'high',
            'due_date': today.isoformat(),
            'category_name': 'Work',
            'estimated_duration': 120,  # 2 hours
            'plan_names': []
        },
        {
            'id': 3,
            'title': 'Task without duration',
            'priority': 'medium',
            'due_date': today.isoformat(),
            'category_name': 'Work',
            'estimated_duration': None,  # Should use default
            'plan_names': []
        },
    ]
    
    events, stats = scheduler.schedule_tasks(tasks)
    
    print(f"\n📅 Scheduled Events with Durations:")
    for event in events:
        duration = event['endMin'] - event['startMin']
        print(f"  {event['title']}: {duration} minutes")
    
    # Verify durations
    assert events[0]['endMin'] - events[0]['startMin'] == 15, "Short task should be 15 min"
    assert events[1]['endMin'] - events[1]['startMin'] == 120, "Long task should be 120 min"
    assert events[2]['endMin'] - events[2]['startMin'] == 45, "Task without duration should use default (45 min)"
    
    print("\n✅ Test 5 Passed!\n")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SMART SCHEDULER TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_basic_scheduling()
        test_priority_ordering()
        test_category_balancing()
        test_rest_blocks()
        test_duration_handling()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
