# Global Default Tasks Setup Guide

## Overview

This system allows you to create global default tasks that are:
- ✅ **Shared across all users** - Every user gets the same set of default tasks
- 🔒 **Protected from editing** - Users cannot modify these tasks
- 🛡️ **Protected from deletion** - Users cannot delete these tasks
- 📂 **Category-based** - One default task is created for each global category

## Purpose

Global default tasks provide a standardized way to track activities across categories without requiring users to create their own tasks. This ensures consistency in activity tracking and prevents accidental deletion of important tracking tasks.

## Quick Start

### Prerequisites

1. Ensure global categories exist:
```bash
python manage.py create_global_categories
```

2. Run the migration (already completed):
```bash
python manage.py migrate tracker
```

### Create Global Default Tasks

**Basic Usage:**
```bash
python manage.py create_global_default_tasks
```

**Dry Run (see what would be created without creating):**
```bash
python manage.py create_global_default_tasks --dry-run
```

**Force Update (recreate even if they exist):**
```bash
python manage.py create_global_default_tasks --force
```

## What Happens

When you run this command:

1. **Scans Global Categories**: Finds all categories marked as `is_global=True`
2. **Scans Active Users**: Finds all active users in the system
3. **Creates Tasks**: For each user and each global category, creates a task with:
   - Title: `{Category Name} Activities` (e.g., "Fitness Activities", "Study Activities")
   - Description: Explains this is a global default task
   - Status: `in_progress`
   - Priority: `medium`
   - `is_global=True`: Marks it as a global task
   - `is_editable=False`: Prevents editing
   - `is_deletable=False`: Prevents deletion

## Example Output

```
🌐 Creating Global Default Tasks...

======================================================================
📋 Found 16 global categories
👥 Found 5 active users
======================================================================

📂 Processing Category: Fitness
----------------------------------------------------------------------
  ✅ john: Created 'Fitness Activities'
  ✅ jane: Created 'Fitness Activities'
  ✅ bob: Created 'Fitness Activities'
  
  Summary: 3 created, 0 skipped

📂 Processing Category: Study
----------------------------------------------------------------------
  ✅ john: Created 'Study Activities'
  ⚠️  jane: Already has global task 'Study Activities'
  ✅ bob: Created 'Study Activities'
  
  Summary: 2 created, 1 skipped

...

======================================================================
🎉 FINAL SUMMARY:
   ✅ Tasks created: 48
   ⚠️  Tasks skipped: 0
   
📊 Total global tasks in database: 48
📂 Categories with global tasks: 16
======================================================================

✨ All users now have default tasks for each global category!
   - These tasks are visible to all users
   - They cannot be edited or deleted
   - Perfect for standardized activity tracking
```

## Database Schema Changes

### New Fields in Task Model

```python
is_global = models.BooleanField(default=False, 
    help_text="Global tasks are shared across all users")

is_editable = models.BooleanField(default=True, 
    help_text="Whether the task can be edited by users")

is_deletable = models.BooleanField(default=True, 
    help_text="Whether the task can be deleted by users")
```

### Migration

- **File**: `tracker/migrations/0013_task_is_deletable_task_is_editable_task_is_global.py`
- **Changes**: Adds three new boolean fields to the Task model

## View Protection

The following views have been updated to respect the new flags:

### task_update (Edit Task)

```python
# Prevents editing if task.is_global and not task.is_editable
if task.is_global and not task.is_editable:
    messages.error(request, "Cannot edit. This is a global default task.")
    return redirect('task_list')
```

### task_delete (Delete Task)

```python
# Prevents deletion if task.is_global and not task.is_deletable
if task.is_global and not task.is_deletable:
    messages.error(request, "Cannot delete. This is a global default task.")
    return redirect('task_list')
```

## Use Cases

### 1. New User Onboarding
When a new user signs up, run the command to give them all default tasks:
```bash
python manage.py create_global_default_tasks
```

### 2. Add New Global Category
After adding a new global category, run the command to create tasks for it:
```bash
python manage.py create_global_default_tasks
```

### 3. System-Wide Update
Force update all global tasks to ensure correct flags:
```bash
python manage.py create_global_default_tasks --force
```

## Troubleshooting

### No Global Categories Found
```
❌ No global categories found!
   Run: python manage.py create_global_categories first
```
**Solution**: Create global categories first.

### No Active Users Found
```
❌ No active users found!
```
**Solution**: Ensure you have active users in the system.

### Tasks Already Exist
If tasks already exist, the command will skip them by default. Use `--force` to update them.

## Advanced: Manual Task Creation

If you need to create a global task manually:

```python
from tracker.models import Task, Category
from django.contrib.auth.models import User

user = User.objects.get(username='john')
category = Category.objects.get(name='Fitness', is_global=True)

Task.objects.create(
    user=user,
    title='Fitness Activities',
    description='Default fitness tracking task',
    category=category,
    status='in_progress',
    priority='medium',
    is_global=True,
    is_editable=False,
    is_deletable=False
)
```

## Integration with Existing Features

### Daily Logs
Users can still create daily logs linked to global tasks. The logs track time spent on these default activities.

### Analytics
Global tasks appear in analytics alongside user-created tasks, providing consistent tracking across all users.

### Calendar Sync
Global tasks can be referenced in calendar events, ensuring standardized activity naming.

## Best Practices

1. ✅ **Create global categories first** before creating global tasks
2. ✅ **Run after adding new users** to ensure they get all default tasks
3. ✅ **Use --dry-run** to preview changes before applying them
4. ✅ **Run periodically** to ensure all users have the latest global tasks
5. ⚠️ **Avoid manual deletion** of global tasks from the database

## Command Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| (none) | Create global tasks for all users and categories | `python manage.py create_global_default_tasks` |
| `--dry-run` | Show what would be created without creating | `python manage.py create_global_default_tasks --dry-run` |
| `--force` | Force creation/update even if tasks exist | `python manage.py create_global_default_tasks --force` |

## Related Commands

- `create_global_categories` - Creates the global categories needed for this command
- `create_default_task` - Creates a single default task (legacy, for backward compatibility)
- `populate_data` - Populates sample data for development

## Support

For issues or questions:
1. Check that migrations have been applied: `python manage.py showmigrations tracker`
2. Verify global categories exist: `python manage.py shell -c "from tracker.models import Category; print(Category.objects.filter(is_global=True).count())"`
3. Review the error messages in the command output for specific guidance
