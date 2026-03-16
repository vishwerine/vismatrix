# Leaderboard & Points System

## Overview
The gamification system rewards users with points for various activities and displays a competitive leaderboard on the dashboard.

## Features Implemented

### 1. Points System
Users earn points for completing various activities:

| Activity | Points | Description |
|----------|--------|-------------|
| **Daily Visit** | +50 | Awarded once per day on first dashboard visit |
| **Log Activity** | +10 | Each time you log a time entry |
| **Receive Star** | +75 | When a friend stars your activity or task |
| **Complete Task** | +100 | When marking a task as complete (once per task) |
| **Accept Mentee** | +100 | When mentor accepts a new mentee |
| **3-Day Streak** | +500 | Bonus for maintaining 3 consecutive daily visits |
| **Complete Plan** | +1000 | When all tasks in a plan are completed (once per plan) |

### 2. Streak Tracking
- **Current Streak**: Counts consecutive daily visits
- **Longest Streak**: Records your best streak ever
- **Streak Bonuses**: 
  - First 3-day streak: +500 points
  - Every subsequent multiple of 3 (6, 9, 12...): +500 points each

### 3. Leaderboard Display
**Location**: Dashboard right sidebar

**Features**:
- Top 10 users by total points
- Trophy medals for top 3 (🥇🥈🥉)
- Your current rank highlighted
- Your stats displayed prominently:
  - Total points
  - Current streak
  - Fire icon for active streaks

### 4. Points Activity Log
Every points transaction is logged with:
- User
- Points earned
- Reason (what action earned the points)
- Timestamp

Viewable in Django admin under "Points Activities"

## Database Models

### UserPoints
```python
- total_points: Total accumulated points
- current_streak: Days of consecutive visits
- longest_streak: Best streak achieved
- last_visit_date: Last dashboard visit date
```

### PointsActivity
```python
- user: Who earned points
- points: Amount earned
- reason: What action earned them
- created_at: When points were earned
```

## Technical Implementation

### Automatic Point Awards
Points are automatically awarded in these views:
1. **dashboard()** - Daily visit and streak tracking
2. **log_create()** - Activity logging
3. **task_complete()** - Task completion
4. **plan_detail()** - Plan completion detection
5. **respond_to_mentorship_request()** - Mentor acceptance
6. **toggle_star_reaction()** - Receiving stars from friends

### Point Award Logic
```python
from tracker.models import UserPoints

# Get or create user points profile
user_points, created = UserPoints.objects.get_or_create(user=request.user)

# Award points with reason
user_points.add_points(100, "Completed task: Task Name")
```

### Streak Update Logic
```python
# Called automatically on dashboard visit
user_points.update_daily_visit()

# Handles:
# - First visit ever
# - Already visited today (skip)
# - Consecutive day (increment streak + bonus)
# - Broken streak (reset to 1)
```

## Admin Interface

### UserPoints Admin
- View all users' points and streaks
- Sort by total points (leaderboard view)
- Search by username
- See last visit dates

### PointsActivity Admin
- Complete audit log of all points earned
- Filter by date and reason
- Search by user
- Chronological order (newest first)

## Management Commands

### Initialize User Points
```bash
python manage.py init_user_points
```
Creates UserPoints profiles for all existing users who don't have one.

## Preventing Duplicate Points

### Task Completion
```python
# Only award once per task
was_completed = task.status == 'completed'
if not was_completed:
    user_points.add_points(100, f"Completed task: {task.title}")
```

### Plan Completion
```python
# Check if already awarded
already_awarded = PointsActivity.objects.filter(
    user=request.user,
    reason__contains=f"Completed plan: {plan.title}"
).exists()

if not already_awarded:
    user_points.add_points(1000, f"Completed plan: {plan.title}")
```

### Daily Visits
```python
# Only award once per day
if self.last_visit_date == today:
    return  # Already visited today
```

## User Experience

### Visual Feedback
- Success messages include points earned: "Activity logged! +10 points"
- Plan completion shows celebration: "🎉 Plan completed! +1000 points!"
- Leaderboard highlights user's position

### Competitive Elements
- Top 3 get medal emojis
- User's rank badge displayed
- Real-time leaderboard updates
- Streak visualization with fire icon

## Future Enhancements (Optional)

### Potential Additions
1. **Badges/Achievements**
   - First task completed
   - 10 tasks completed
   - Week streak master
   - Plan completionist

2. **Point Multipliers**
   - Weekend bonus (2x points)
   - Category-specific bonuses
   - Friend collaboration bonuses

3. **Leaderboard Variants**
   - Weekly leaderboard (resets)
   - Friends-only leaderboard
   - Category-specific leaderboards

4. **Rewards/Redemption**
   - Spend points on profile customization
   - Unlock special features
   - Virtual rewards/badges

5. **Analytics**
   - Points earned over time graph
   - Streak history visualization
   - Activity breakdown by points source

## Migration Information

**Migration**: `0017_pointsactivity_userpoints.py`

**Created Models**:
- PointsActivity
- UserPoints

**Indexes**:
- UserPoints: total_points (DESC) for leaderboard performance
- UserPoints: user, is_read, created_at for notifications

## Testing Checklist

- [ ] Dashboard shows leaderboard
- [ ] Daily visit awards 50 points
- [ ] Logging activity awards 10 points
- [ ] Completing task awards 100 points
- [ ] Accepting mentee awards 100 points
- [ ] 3-day streak awards 500 bonus
- [ ] Completing plan awards 1000 points
- [ ] No duplicate points for same action
- [ ] Leaderboard updates in real-time
- [ ] User rank displays correctly
- [ ] Streak tracking works across days
- [ ] Points activity log is accurate

## API Endpoints

None currently exposed. All points logic is server-side.

## Performance Considerations

- Leaderboard query is optimized with indexes
- Only top 10 users fetched for dashboard
- User rank calculated efficiently with single count query
- Points transactions are lightweight (no complex calculations)

## Security

- Points can only be awarded server-side
- No user-facing API to manipulate points
- All point awards require authentication
- Admin-only access to manual adjustments
