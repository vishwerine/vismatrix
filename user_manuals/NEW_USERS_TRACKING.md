# New Users Tracking Feature

## Overview
Admin-only dashboard to track and monitor new user registrations in the VisMatrix application.

## Access
- **URL**: `/admin-analytics/new-users/`
- **Route Name**: `new_users_tracking`
- **Permission**: Staff members only (`@staff_member_required`)
- **Navigation**: Available in user dropdown menu (top-right) under "Admin" section (only visible to staff users)

## Features

### 📊 Key Metrics
- **Total Users**: Complete count of all registered users
- **New Users**: Count of users who joined within the selected time period
- **Active Users**: Users who logged in within the last 7 days

### 📈 Daily Signup Trend
Interactive chart showing daily user registration trends over the selected time period.

### 👥 User List
Comprehensive table displaying:
- **User Information**:
  - Username with role badges (SUPERUSER/STAFF)
  - Full name (if provided)
  - Email address
- **Timeline**:
  - Join date and time
  - Last login date and relative time ("X days ago")
- **Status Indicators**:
  - 🟢 Active: Logged in within the last 7 days
  - 🟡 Inactive: Registered but hasn't logged in for 7+ days
  - ⚪ Never Logged In: Account created but never accessed
  - ⚫ Disabled: Account is deactivated

### 🔍 Filtering Options
- **Last 7 Days**: Recent signups
- **Last 30 Days**: Monthly overview
- **Last 90 Days**: Quarterly view
- **All Time**: Complete user history (default)

### 📄 Pagination
- 50 users per page
- Easy navigation between pages
- Maintains filter selections during pagination

## Implementation Details

### Files Modified/Created

1. **View** (`tracker/views.py`):
   - Added `new_users_tracking()` function
   - Uses `@staff_member_required` decorator for access control
   - Queries User model ordered by `date_joined` (descending)
   - Calculates daily signup trends
   - Implements pagination

2. **URL** (`tracker/urls.py`):
   - Added route: `path("admin-analytics/new-users/", views.new_users_tracking, name="new_users_tracking")`

3. **Template** (`tracker/templates/tracker/admin_new_users.html`):
   - Modern responsive design matching existing analytics pages
   - Chart.js integration for trend visualization
   - Dark mode support
   - Mobile-friendly table layout

4. **Navigation** (`tracker/templates/tracker/base.html`):
   - Added admin section in user dropdown menu
   - Links to both new users tracking and landing analytics
   - Only visible to staff members

## Usage

### For Admin Users:
1. Login with an admin/staff account
2. Click on your profile avatar (top-right)
3. Navigate to "Admin" → "New Users Tracking"
4. Select desired time period using filter buttons
5. View metrics, trends, and detailed user list
6. Use pagination to browse through all users

### Security
- Automatically redirects non-admin users to login page
- Uses Django's built-in `staff_member_required` decorator
- No special configuration needed

## Technical Notes

- **ORM Query Optimization**: Uses `select_related('userprofile')` to prevent N+1 queries
- **Timezone Aware**: All timestamps use Django's timezone utilities
- **Performance**: Pagination limits database load for large user bases
- **Responsive**: Fully functional on mobile, tablet, and desktop devices

## Future Enhancements (Optional)
- Export user list to CSV
- Advanced filters (by email domain, activity level, etc.)
- User engagement metrics
- Cohort analysis
- Email verification status
- User retention graphs

## Support
For issues or questions, contact the development team or check the main README.md in the user_manuals directory.
