# Shared Global Default Tasks - Updated Implementation

## Overview

The system now creates **16 shared global tasks** (one per category) that are:
- ✅ **Shared across ALL users** - Single task instance visible to everyone
- 🔒 **Protected from editing** - Cannot be modified by any user
- 🛡️ **Protected from deletion** - Cannot be deleted by any user
- 📅 **50-year deadline** - Due date set 50 years from creation
- 👤 **System-owned** - Belong to `system_global` user

## Key Changes from Previous Implementation

### Before (Old Approach)
- Created separate task copies for each user
- 5 users × 16 categories = 80 tasks total
- Each user had their own copy: "username - Fitness Activities"
- Duplicated data across users

### After (New Approach)
- Creates only 16 shared tasks (one per category)
- All tasks belong to `system_global` user
- All users see the same task instances
- Cleaner, more efficient design

## Quick Start

### Create Shared Global Tasks

```bash
# Basic usage - creates 16 shared tasks
python manage.py create_global_default_tasks

# With cleanup - removes old per-user tasks first
python manage.py create_global_default_tasks --cleanup

# Dry run - preview without creating
python manage.py create_global_default_tasks --dry-run

# Force update - update existing tasks
python manage.py create_global_default_tasks --force
```

## What Was Changed

### 1. Management Command ([create_global_default_tasks.py](../progress_tracker/tracker/management/commands/create_global_default_tasks.py))

**Before:** Created tasks for each user individually
```python
for user in users:
    Task.objects.create(user=user, ...)  # 5 users = 5 tasks per category
```

**After:** Creates one task per category under system user
```python
system_user = User.objects.get_or_create(username='system_global')
Task.objects.create(
    user=system_user,
    due_date=timezone.now().date() + timedelta(days=365 * 50),  # 50 years
    ...
)
```

### 2. Task List View ([tracker/views.py](../progress_tracker/tracker/views.py#L733-L750))

Updated to show system user's global tasks to all users:

```python
# Get user's own tasks AND global tasks from system user
if system_user:
    tasks = Task.objects.filter(
        Q(user=request.user) | Q(user=system_user, is_global=True)
    ).select_related('category')
```

### 3. Forms ([tracker/forms.py](../progress_tracker/tracker/forms.py))

Updated `DailyLogForm` and `PlanNodeForm` to include global tasks in dropdowns:

```python
# Show user's tasks AND global tasks from system_global user
system_user = User.objects.get(username='system_global')
self.fields['task'].queryset = Task.objects.filter(
    Q(user=user) | Q(user=system_user, is_global=True)
)
```

## Verification

### Check Global Tasks

```bash
python manage.py shell
```

```python
from tracker.models import Task
from django.contrib.auth.models import User

system_user = User.objects.get(username='system_global')
global_tasks = Task.objects.filter(user=system_user, is_global=True)

print(f"Total shared global tasks: {global_tasks.count()}")  # Should be 16

# Check one task
task = global_tasks.first()
print(f"Title: {task.title}")
print(f"User: {task.user.username}")  # system_global
print(f"Due date: {task.due_date}")  # 2075-12-16 (50 years from now)
print(f"Editable: {task.is_editable}")  # False
print(f"Deletable: {task.is_deletable}")  # False
```

### Current Status

✅ **16 shared global tasks created**
- Each belongs to `system_global` user
- Due date: **2075-12-16** (50 years from 2025-12-28)
- All categories covered:
  - Fitness, Freelance, Goals, Habits, Health
  - Hobbies, Interviews, Job Search, Journaling, Languages
  - Meditation, Projects, Reading, Skills, Study, Work

✅ **Old per-user tasks cleaned up**
- Previous 80 tasks (per-user copies) can be removed with `--cleanup` flag

✅ **Views updated**
- Task list shows global tasks to all users
- Forms include global tasks in dropdowns

✅ **Protection enforced**
- Edit/delete views block modifications to global tasks
- User-friendly error messages displayed

## Usage Example

### For End Users

When users view their task list, they will see:
1. **Their own tasks** - Created by them, can edit/delete
2. **Shared global tasks** - System tasks, cannot edit/delete

Example task list for user "john":
```
Your Tasks:
  - Personal Project (editable/deletable)
  - Study Python (editable/deletable)
  
Global Tasks (shared):
  - Fitness Activities (protected) ← 🔒
  - Study Activities (protected) ← 🔒
  - Work Activities (protected) ← 🔒
  ... (all 16 categories)
```

### Creating Daily Logs

Users can select from both personal and global tasks:
```
Create Daily Log
  Task: [dropdown]
    - Personal Project (your task)
    - Study Python (your task)
    - Fitness Activities (global) ← Can select
    - Study Activities (global) ← Can select
    ...
```

## Command Options

| Option | Description | Example |
|--------|-------------|---------|
| (none) | Create 16 shared tasks under system_global user | `python manage.py create_global_default_tasks` |
| `--cleanup` | Remove old per-user global tasks before creating | `python manage.py create_global_default_tasks --cleanup` |
| `--dry-run` | Preview without creating | `python manage.py create_global_default_tasks --dry-run` |
| `--force` | Update existing tasks | `python manage.py create_global_default_tasks --force` |

## Benefits of New Approach

1. **Efficiency**: 16 tasks instead of 80+ (scales better with more users)
2. **Consistency**: All users see identical global tasks
3. **Maintenance**: Update once affects all users
4. **Clarity**: Clear distinction between personal and global tasks
5. **Scalability**: Adding 100 users doesn't create 1600+ global tasks

## Database Impact

### System User
- **Username**: `system_global`
- **Email**: `system@vismatrix.space`
- **Purpose**: Owns all shared global tasks
- **Status**: Active, non-staff, non-superuser

### Task Distribution
- **Old**: 5 users × 16 categories = 80 tasks
- **New**: 1 system user × 16 categories = 16 tasks
- **Savings**: 80% reduction in global task records

## Migration Notes

If you're upgrading from the old per-user approach:

1. **Backup your data** (recommended)
2. **Run with cleanup flag**:
   ```bash
   python manage.py create_global_default_tasks --cleanup
   ```
3. **Verify**: Check that old tasks are removed and new ones created
4. **Restart server**: Ensure views pick up the changes

## Files Changed

1. **[create_global_default_tasks.py](../progress_tracker/tracker/management/commands/create_global_default_tasks.py)** - Management command
2. **[views.py](../progress_tracker/tracker/views.py)** - Task list view (line ~733)
3. **[forms.py](../progress_tracker/tracker/forms.py)** - DailyLogForm & PlanNodeForm (lines ~105, ~188)

## Related Documentation

- [GLOBAL_DEFAULT_TASKS.md](GLOBAL_DEFAULT_TASKS.md) - Original documentation
- [GLOBAL_DEFAULT_TASKS_QUICK_REF.md](GLOBAL_DEFAULT_TASKS_QUICK_REF.md) - Quick reference

---

**Last Updated**: 2025-12-28  
**Implementation**: Shared global tasks with 50-year deadline
