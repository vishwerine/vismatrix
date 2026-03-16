# Quick Reference: Global Default Tasks

## What It Does
Creates one default task for each global category for every user in the system. These tasks are:
- 🔒 **Not editable** by users
- 🛡️ **Not deletable** by users  
- 📂 **One per global category** (e.g., "Fitness Activities", "Study Activities")
- 👥 **Shared across all users** (each user gets their own copy)

## Usage

```bash
# Create tasks for all users and categories
python manage.py create_global_default_tasks

# Preview what would be created (recommended first)
python manage.py create_global_default_tasks --dry-run

# Force recreate/update existing tasks
python manage.py create_global_default_tasks --force
```

## When to Run

✅ After adding new users to the system  
✅ After creating new global categories  
✅ During initial system setup  
✅ After database migrations  

## Prerequisites

1. Global categories must exist:
   ```bash
   python manage.py create_global_categories
   ```

2. Migration must be applied (done):
   ```bash
   python manage.py migrate tracker
   ```

## Example Results

For 5 users and 16 global categories:
- **Creates**: 80 tasks (5 users × 16 categories)
- **Task titles**: "Fitness Activities", "Study Activities", etc.
- **All tasks have**: `is_global=True`, `is_editable=False`, `is_deletable=False`

## Files Modified/Created

### Models
- [tracker/models.py](../progress_tracker/tracker/models.py) - Added `is_global`, `is_editable`, `is_deletable` fields to Task model

### Views  
- [tracker/views.py](../progress_tracker/tracker/views.py) - Added protection in `task_update` and `task_delete` views

### Migration
- `tracker/migrations/0013_task_is_deletable_task_is_editable_task_is_global.py`

### Management Command
- [tracker/management/commands/create_global_default_tasks.py](../progress_tracker/tracker/management/commands/create_global_default_tasks.py)

### Documentation
- [GLOBAL_DEFAULT_TASKS.md](GLOBAL_DEFAULT_TASKS.md) - Complete guide

## Protection Logic

### In Views (Automatic)

**Edit Protection:**
```python
if task.is_global and not task.is_editable:
    messages.error(request, "Cannot edit global task")
    return redirect('task_list')
```

**Delete Protection:**
```python
if task.is_global and not task.is_deletable:
    messages.error(request, "Cannot delete global task")
    return redirect('task_list')
```

## Verification

Check created tasks:
```bash
python manage.py shell
>>> from tracker.models import Task
>>> Task.objects.filter(is_global=True).count()
80  # For 5 users × 16 categories
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No global categories found" | Run `create_global_categories` first |
| "No active users found" | Create users or activate existing ones |
| Tasks already exist | Use `--force` flag to update them |
| Edit/delete still works | Restart Django server after migration |

## Full Documentation

See [GLOBAL_DEFAULT_TASKS.md](GLOBAL_DEFAULT_TASKS.md) for complete details.
