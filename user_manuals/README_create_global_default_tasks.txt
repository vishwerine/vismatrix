"""
Django Management Command: create_global_default_tasks
======================================================

PURPOSE
-------
Creates global default tasks (one per global category) for all active users.
These tasks are shared across all users but are protected from editing and deletion.

USAGE
-----
    python manage.py create_global_default_tasks [--dry-run] [--force]

OPTIONS
-------
    --dry-run
        Preview what would be created without actually creating tasks.
        Use this to see the impact before making changes.
        
    --force
        Force creation/update even if tasks already exist.
        Updates existing tasks to ensure correct protection flags.

PREREQUISITES
-------------
1. Global categories must exist:
   python manage.py create_global_categories

2. Migration must be applied:
   python manage.py migrate tracker

WHAT IT DOES
------------
For each active user and each global category:
1. Creates a task with title "{Category} Activities"
2. Sets description explaining it's a global default task
3. Marks as: is_global=True, is_editable=False, is_deletable=False
4. Sets status to 'in_progress' and priority to 'medium'

EXAMPLES
--------
# Preview what would be created
python manage.py create_global_default_tasks --dry-run

# Create tasks for all users and categories
python manage.py create_global_default_tasks

# Force update existing tasks
python manage.py create_global_default_tasks --force

OUTPUT
------
The command provides detailed output including:
- Number of global categories and users found
- Progress for each category showing created/skipped tasks
- Final summary with statistics
- Total global tasks in database

EXPECTED RESULTS
----------------
For 5 users and 16 global categories:
- Creates: 80 tasks (5 × 16)
- Each user gets: 16 tasks (one per category)
- All tasks are: Protected from editing and deletion

ERROR HANDLING
--------------
- "No global categories found": Run create_global_categories first
- "No active users found": Ensure you have active users
- Individual errors are logged but don't stop the process

VERIFICATION
------------
After running, verify with:
    python manage.py shell
    >>> from tracker.models import Task
    >>> Task.objects.filter(is_global=True).count()
    >>> Task.objects.filter(is_global=True).first().__dict__

Or use the test script:
    python manage.py shell < test_global_tasks.py

RELATED FILES
-------------
- Models: tracker/models.py (Task model with global flags)
- Views: tracker/views.py (protection logic for edit/delete)
- Migration: 0013_task_is_deletable_task_is_editable_task_is_global.py
- Tests: test_global_tasks.py
- Docs: user_manuals/GLOBAL_DEFAULT_TASKS.md

AUTHOR
------
Created for the Progress Tracker system to provide standardized
activity tracking across all users.

SEE ALSO
--------
- create_global_categories: Creates the categories used by this command
- create_default_task: Legacy command for creating single default task
"""
