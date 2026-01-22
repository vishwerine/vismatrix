# VisMatrix Pro Features Documentation

## Overview

VisMatrix Pro is a premium subscription tier ($20/month) that unlocks advanced productivity features, AI-powered tools, and enhanced analytics capabilities.

## Pro Features

### 1. 🚀 Advanced Analytics Dashboard
**URL**: `/pro/analytics/`

**Features**:
- Detailed task statistics with priority-based breakdown
- Week-over-week productivity comparison
- Time distribution by category (top 10)
- Daily productivity trend charts (minutes + tasks completed)
- Habit success rate analysis
- Completion rates by priority level
- Average task completion time by category

**Key Metrics**:
- Total tasks, completed, in progress, overdue
- Week change percentage with visual indicators
- Category time tracking with log counts
- Habit streak analysis (current vs best)

**Export Options**:
- Quick export buttons for tasks, logs, habits, and analytics summary

---

### 2. 📊 Data Export (CSV Format)
**URL**: `/pro/export/csv/`

**Export Types**:

#### Tasks Export
- Title, Description, Status, Priority
- Due Date, Created Date, Completed Date
- Category, Estimated Duration, Actual Duration

#### Logs Export
- Date, Activity, Duration (minutes)
- Description, Category, Associated Task

#### Habits Export
- Habit Name, Frequency, Active Status
- Current Streak, Best Streak
- Creation Date, Total Completions

#### Analytics Summary Export
- Total tasks and completion rate
- Total logs and time logged (hours)
- Total plans (active and inactive)
- Export timestamp

**Usage**:
```
GET /pro/export/csv/?type=tasks
GET /pro/export/csv/?type=logs
GET /pro/export/csv/?type=habits
GET /pro/export/csv/?type=analytics
```

---

### 3. 🤖 AI Auto-Categorization
**URL**: `/pro/api/ai-categorize/`

**Functionality**:
- Uses semantic classifier to automatically categorize tasks
- Analyzes task title and description
- Creates or assigns appropriate category
- Powered by pre-trained ML model

**API Endpoint**:
```javascript
POST /pro/api/ai-categorize/
{
  "task_id": 123
}

Response:
{
  "success": true,
  "category": "Programming",
  "category_id": 5,
  "message": "Task categorized as: Programming"
}
```

**Requirements**:
- `classifier_service.py` must be available
- Task must belong to the requesting user
- Cannot categorize global tasks

---

### 4. 📦 Bulk Operations
**URL**: `/pro/api/bulk-operations/`

**Supported Operations**:

#### For Tasks:
- **Delete**: Remove multiple tasks at once
- **Complete**: Mark multiple tasks as completed
- **Reopen**: Change status back to pending
- **Update Priority**: Batch change priority level
- **Update Category**: Assign category to multiple tasks

#### For Logs:
- **Delete**: Remove multiple log entries
- **Update Category**: Batch update category

**API Usage**:
```javascript
POST /pro/api/bulk-operations/
{
  "operation": "complete",
  "type": "tasks",
  "ids": [1, 2, 3, 4, 5]
}

// For category updates
{
  "operation": "update_category",
  "type": "tasks",
  "ids": [1, 2, 3],
  "category_id": 7
}

Response:
{
  "success": true,
  "count": 5,
  "message": "Marked 5 tasks as complete"
}
```

**Security**:
- All operations restricted to user's own data
- Global tasks cannot be modified
- Atomic operations with proper error handling

---

### 5. ⭐ Pro Dashboard
**URL**: `/pro/`

**Dashboard Sections**:

#### Pro Features Overview
- Interactive cards for all Pro features
- Quick access to Advanced Analytics
- Direct links to data exports
- AI categorization info
- Bulk operations access
- Unlimited history badge
- Priority support info

#### Subscription Details
- Current plan and status
- Billing period (start and end dates)
- Days remaining in current period
- Renewal date
- Manage subscription button (Stripe portal)

#### Payment History
- Last 5 payments displayed
- Amount, date, and status
- Link to full payment history
- Visual status badges (success/failed)

#### Feature Usage Stats
- Total data exports count
- Total bulk operations performed
- Total AI classifications used

---

## User Interface Enhancements

### Navigation Menu
**Pro Users See**:
- ⭐ Pro dropdown menu in navbar
- Quick access to Pro Dashboard
- Advanced Analytics link
- Export shortcuts (Tasks, Logs)

**Free Users See**:
- Locked Pro features with 🔒 icon
- Upgrade prompts
- Badge showing "Free" plan

### Analytics Page Banners
**Pro Users**:
- Purple gradient banner
- "Unlock Deeper Insights" message
- Direct link to Advanced Analytics

**Free Users**:
- Upgrade prompt banner
- List of Pro benefits
- Call-to-action button

### Task List Page
**Pro Users**:
- "Bulk Edit" button with Pro badge
- Functional bulk selection mode

**Free Users**:
- Locked "Bulk Edit" button
- Tooltip: "Upgrade to Pro"
- Click redirects to subscription page

---

## Access Control

### @pro_required Decorator
All Pro features are protected by the `@pro_required()` decorator:

```python
from tracker.decorators import pro_required

@login_required
@pro_required()
def my_pro_feature(request):
    # Only accessible to Pro subscribers
    pass
```

**Behavior**:
- Checks `request.user.subscription.is_pro`
- Redirects non-Pro users to subscription plans page
- Shows warning message: "This feature requires a Pro subscription"
- Allows Pro users to access the feature

### Template Context
All templates have access to `user_subscription` context:

```django
{% if user_subscription.is_pro %}
  <!-- Show Pro features -->
{% else %}
  <!-- Show upgrade prompt -->
{% endif %}
```

---

## Subscription Management

### Stripe Integration
- **Checkout**: Handled by Stripe Checkout
- **Price**: $20.00/month recurring
- **Test Card**: 4242 4242 4242 4242

### Subscription Status
- `active`: Full Pro access
- `past_due`: Payment issue, access maintained
- `canceled`: Subscription ended, downgraded to Free
- `incomplete`: Payment pending

### Portal Access
Users can manage subscriptions via Stripe Customer Portal:
- Update payment method
- View invoices
- Cancel subscription
- Update billing info

**URL**: `/subscription/portal/`

---

## Feature Comparison

| Feature | Free | Pro |
|---------|------|-----|
| Basic Analytics | ✅ | ✅ |
| Advanced Analytics | ❌ | ✅ |
| Data Export (JSON) | ✅ | ✅ |
| Data Export (CSV) | ❌ | ✅ |
| AI Auto-Categorization | ❌ | ✅ |
| Bulk Operations | ❌ | ✅ |
| History Limit | 90 days | Unlimited |
| Calendar Sync | ✅ | ✅ |
| Task Management | ✅ | ✅ |
| Plans & DAG | ✅ | ✅ |
| Social Features | ✅ | ✅ |
| Priority Support | ❌ | ✅ |
| Custom Themes | Coming Soon | Coming Soon |

---

## Installation & Setup

### 1. Files Added
- `/tracker/pro_views.py` - All Pro feature views
- `/tracker/templates/tracker/pro_analytics.html` - Advanced analytics
- `/tracker/templates/tracker/pro_dashboard.html` - Pro dashboard

### 2. URL Configuration
Add to `tracker/urls.py`:
```python
from . import pro_views

urlpatterns = [
    # ... existing patterns ...
    path("pro/", pro_views.pro_features_dashboard, name="pro_dashboard"),
    path("pro/analytics/", pro_views.advanced_analytics, name="advanced_analytics"),
    path("pro/export/csv/", pro_views.export_data_csv, name="export_data_csv"),
    path("pro/api/bulk-operations/", pro_views.bulk_operations, name="bulk_operations"),
    path("pro/api/ai-categorize/", pro_views.ai_categorize_task, name="ai_categorize_task"),
]
```

### 3. Template Updates
- `base.html`: Added Pro menu in navbar
- `analytics.html`: Added Pro upgrade banner
- `task_list.html`: Added bulk operations button

---

## Future Enhancements

### Planned Features
1. **PDF Export**: Generate beautiful PDF reports
2. **Custom Themes**: Multiple color schemes for Pro users
3. **Advanced Filters**: Saved searches and complex filters
4. **Predictive Analytics**: AI-powered productivity predictions
5. **API Access**: RESTful API for integrations
6. **Team Collaboration**: Share plans with team members
7. **Priority Support**: Dedicated support channel
8. **Mobile App**: Native iOS/Android apps

### Analytics Enhancements
- Time-of-day productivity heatmap
- Project-based time tracking
- Eisenhower matrix visualization
- Burndown charts for goals
- Habit correlation analysis

---

## Troubleshooting

### Pro Features Not Working

**Check Subscription Status**:
```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='your_username')
>>> print(user.subscription.plan)
>>> print(user.subscription.is_pro)
```

**Common Issues**:
1. **Subscription expired**: Renew via Stripe portal
2. **Payment failed**: Update payment method
3. **Cache issue**: Clear browser cache and Django cache
4. **Decorator missing**: Ensure `@pro_required()` on views

### AI Categorization Not Working

**Requirements**:
1. `classifier_service.py` must exist in project root
2. ML model files must be present
3. Required packages installed:
   ```bash
   pip install scikit-learn numpy
   ```

**Debug**:
```python
import sys
sys.path.insert(0, '/path/to/vismatrix')
from classifier_service import classify_text
result = classify_text("Study Python programming")
print(result)
```

---

## Support

### For Pro Users
- Email: support@vismatrix.space
- Priority response: Within 24 hours
- Direct access to development team

### For Free Users
- Community forum
- Documentation
- Email support: Within 48-72 hours

---

## Pricing

**Pro Plan**: $20.00/month
- Billed monthly via Stripe
- Cancel anytime
- Immediate access upon payment
- 30-day money-back guarantee (contact support)

**Test Mode**:
- Use test card: 4242 4242 4242 4242
- Any future expiry date
- Any CVC

---

## Legal

### Subscription Terms
- Auto-renewal every 30 days
- Cancel anytime via Stripe portal
- No refunds for partial months
- Access continues until period end after cancellation

### Data Ownership
- All user data belongs to the user
- Pro users can export data anytime
- Data deleted 30 days after account deletion

---

## Credits

**Built with**:
- Django 5.2.8
- Stripe Payments
- Chart.js for visualizations
- TailwindCSS + DaisyUI
- Scikit-learn for AI features

**Developed by**: VisMatrix Team
**Version**: 1.0.0
**Last Updated**: January 2026
