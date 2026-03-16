# Leaderboard Feature - Quick Reference

## What's New?
A gamification system that rewards users with points for productivity activities and displays a competitive leaderboard.

## How to Earn Points

```
Daily Visit          → +50 points  (once per day)
Log Activity         → +10 points  (each log entry)
Receive Star         → +75 points  (from friends)
Complete Task        → +100 points (once per task)
Accept Mentee        → +100 points (mentors only)
3-Day Streak Bonus   → +500 points (every 3 consecutive days)
Complete Plan        → +1000 points (once per plan)
```

## Where to See It
**Dashboard → Right Sidebar → Leaderboard Card**

Shows:
- Your total points & current rank
- Your daily visit streak
- Top 10 users (🥇🥈🥉 for top 3)
- How to earn more points

## Key Features
1. **Automatic Point Awards** - No manual action needed
2. **Streak Tracking** - Visit daily to build your streak
3. **Fair Competition** - No duplicate points for same actions
4. **Real-time Updates** - Leaderboard refreshes on each dashboard visit

## Admin Access
- **UserPoints** - View all user scores and streaks
- **PointsActivity** - Complete audit log of all points earned

## Setup for Existing Users
```bash
python manage.py init_user_points
```

## Files Modified
- `models.py` - Added UserPoints, PointsActivity models
- `views.py` - Added point awards to 5 key views
- `admin.py` - Registered new models
- `dashboard.html` - Added leaderboard display

## Migration
`0017_pointsactivity_userpoints.py` - Applied successfully ✅
