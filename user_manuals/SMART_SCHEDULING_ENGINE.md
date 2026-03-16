# Smart Auto-Scheduling Engine

## Overview

The Day Planner now features an **intelligent auto-scheduling engine** that creates optimized daily schedules based on multiple factors including task priority, due dates, estimated duration, and category balance. This replaces the previous simple random task allocation with a sophisticated algorithm that helps users plan their day more effectively.

## Features

### 🧠 Intelligent Task Prioritization

The scheduler considers multiple factors when deciding task order:

1. **Due Date Urgency** (highest weight)
   - Overdue tasks: +200 points
   - Due today: +150 points
   - Due tomorrow: +100 points
   - Due within 3 days: +75 points
   - Due within a week: +50 points
   - Due later: diminishing priority

2. **Task Priority Level**
   - High priority: +100 points
   - Medium priority: +50 points
   - Low priority: +25 points

3. **Category Balance**
   - Penalizes overused categories (-15 points per task already scheduled)
   - Encourages variety in task types throughout the day

### ⏱️ Smart Duration Handling

- Uses task's `estimated_duration` field when available
- Falls back to 45-minute default for tasks without duration
- Enforces minimum (15 min) and maximum (120 min) bounds
- Respects these durations when creating the schedule

### ☕ Automatic Rest Blocks

- Inserts 10-minute breaks between tasks automatically
- Rest time is tracked separately from work time
- Helps prevent burnout and maintains productivity

### 📊 Category Balancing

- Distributes different types of tasks throughout the day
- Prevents scheduling all similar tasks consecutively
- Creates a more varied and engaging work schedule

## Architecture

### Backend Components

#### 1. Smart Scheduler Service (`smart_scheduler.py`)

```python
class SmartScheduler:
    - calculate_task_score(): Scores tasks based on multiple factors
    - get_task_duration(): Gets task duration with fallbacks
    - schedule_tasks(): Main scheduling algorithm
```

**Location**: `/tracker/services/smart_scheduler.py`

The scheduler uses a dynamic scoring system that recalculates priorities after each task is scheduled, ensuring optimal category balance.

#### 2. API Endpoint (`views.py`)

**Endpoint**: `POST /api/day-schedule/smart-schedule/`

**Request Format**:
```json
{
  "date": "2025-12-29",
  "start_time": "09:00",
  "end_time": "17:00"
}
```

**Response Format**:
```json
{
  "success": true,
  "events": [
    {
      "id": "auto_1_0",
      "title": "High Priority Task",
      "startMin": 540,
      "endMin": 600,
      "logged": false,
      "planNames": ["Project X"],
      "taskId": 1,
      "category": "Programming",
      "priority": "high",
      "isCalendarEvent": false
    }
  ],
  "stats": {
    "scheduled_count": 5,
    "total_work_time": 225,
    "total_rest_time": 40,
    "unscheduled_count": 2,
    "category_distribution": {
      "Programming": 3,
      "Design": 1,
      "Meetings": 1
    }
  }
}
```

#### 3. URL Configuration

Added to `urls.py`:
```python
path("api/day-schedule/smart-schedule/", views.smart_schedule_tasks, name="smart_schedule_tasks")
```

### Frontend Integration

#### Updated Modal UI

The auto-schedule modal now clearly communicates the intelligent features:

- **Smart scheduling indicators**: Shows what factors are considered
- **Live preview**: Displays how many tasks can fit in the time window
- **Enhanced feedback**: Shows detailed statistics after scheduling

#### API Integration

The frontend now:
1. Calls the backend API instead of doing client-side scheduling
2. Displays loading state during scheduling
3. Shows detailed success message with statistics
4. Handles errors gracefully

## Usage

### For Users

1. Navigate to **Day Planner**
2. Click **"Auto Schedule"** button
3. Select time window (start and end times)
4. Click **"Create Smart Schedule"**
5. View the optimized schedule with statistics

### For Developers

#### Adding New Scoring Factors

To add new factors to the scoring algorithm, modify `calculate_task_score()` in `smart_scheduler.py`:

```python
def calculate_task_score(self, task: Dict, category_usage: Dict[str, int]) -> float:
    score = 0.0
    
    # Add your new factor here
    if task.get('is_blocked'):
        score -= 50  # Lower priority for blocked tasks
    
    return score
```

#### Customizing Rest Block Duration

Modify the class constant in `SmartScheduler`:

```python
REST_BLOCK_DURATION = 10  # Change this value (in minutes)
```

#### Adjusting Default Task Duration

```python
DEFAULT_TASK_DURATION = 45  # Change this value (in minutes)
```

## Testing

A comprehensive test suite is included at `/progress_tracker/test_smart_scheduler.py`

**Run tests**:
```bash
cd progress_tracker
python test_smart_scheduler.py
```

**Test Coverage**:
- ✅ Basic scheduling functionality
- ✅ Priority ordering (due date + priority level)
- ✅ Category balancing
- ✅ Rest block insertion
- ✅ Duration handling (custom, default, bounds)

All tests pass successfully! 🎉

## Benefits

### For Users

1. **Save Time**: No manual task arrangement needed
2. **Better Planning**: Urgent tasks are prioritized automatically
3. **Balanced Workday**: Variety in task types prevents monotony
4. **Realistic Scheduling**: Considers actual task durations
5. **Built-in Breaks**: Automatic rest blocks promote well-being

### For Productivity

1. **Higher Completion Rates**: Priority tasks scheduled first
2. **Reduced Decision Fatigue**: Algorithm handles optimization
3. **Better Time Estimation**: Duration-aware scheduling
4. **Sustainable Pace**: Regular breaks prevent burnout

## Future Enhancements

Possible improvements for future versions:

1. **Machine Learning**: Learn from user's completion patterns
2. **Energy Levels**: Consider time-of-day preferences
3. **Dependencies**: Respect task dependencies from plans
4. **Focus Blocks**: Group similar tasks for deep work sessions
5. **Conflict Detection**: Avoid scheduling over calendar events
6. **Customizable Weights**: Let users adjust priority factors
7. **Team Scheduling**: Coordinate with team members' schedules

## Technical Details

### Algorithm Complexity

- **Time Complexity**: O(n² × log n) where n is number of tasks
  - O(n) iterations (one per task to schedule)
  - O(n log n) sorting in each iteration
  - O(n) scoring in each iteration

- **Space Complexity**: O(n) for storing events and statistics

### Performance Considerations

- Efficient for typical use cases (< 50 tasks)
- Rescoring after each task ensures optimal results
- Early termination if no tasks fit remaining time

### Database Impact

- Read-only operation on Task model
- No database writes during scheduling calculation
- Results saved via existing `save_day_schedule` endpoint

## Migration Notes

### Changes from Previous Version

**Old Behavior**:
- Simple equal time distribution
- No priority consideration
- Random task order
- Fixed task duration

**New Behavior**:
- Intelligent priority scoring
- Dynamic task duration
- Category-balanced scheduling
- Automatic rest blocks

### Backward Compatibility

✅ Fully backward compatible:
- Existing schedules unaffected
- Same API endpoint paths
- Same data models
- Graceful fallback for tasks without duration

## Support

For issues or questions:
1. Check test suite for examples
2. Review algorithm in `smart_scheduler.py`
3. Inspect API response format in `views.py`
4. Test with sample data using test script

---

**Created**: December 29, 2025  
**Version**: 1.0  
**Status**: ✅ Production Ready
