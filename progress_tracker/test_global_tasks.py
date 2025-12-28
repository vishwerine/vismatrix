"""
Test script for Global Default Tasks functionality
Run with: python manage.py shell < test_global_tasks.py
"""

from tracker.models import Task, Category
from django.contrib.auth.models import User

print("=" * 70)
print("TESTING GLOBAL DEFAULT TASKS")
print("=" * 70)

# Check if we have global categories
global_categories = Category.objects.filter(is_global=True)
print(f"\n✅ Global categories found: {global_categories.count()}")

if global_categories.count() > 0:
    print("   Sample categories:")
    for cat in global_categories[:5]:
        print(f"   - {cat.name}")

# Check if we have users
users = User.objects.filter(is_active=True)
print(f"\n✅ Active users found: {users.count()}")

if users.count() > 0:
    print("   Users:")
    for user in users:
        print(f"   - {user.username}")

# Check if global tasks exist
global_tasks = Task.objects.filter(is_global=True)
print(f"\n📊 Global tasks in database: {global_tasks.count()}")

if global_tasks.count() > 0:
    print("\n   Sample global tasks:")
    for task in global_tasks[:10]:
        print(f"   - {task.user.username}: {task.title}")
        print(f"     └ Editable: {task.is_editable}, Deletable: {task.is_deletable}")
    
    # Check task properties
    sample_task = global_tasks.first()
    print(f"\n🔍 Detailed check of first global task:")
    print(f"   Title: {sample_task.title}")
    print(f"   User: {sample_task.user.username}")
    print(f"   Category: {sample_task.category.name if sample_task.category else 'None'}")
    print(f"   is_global: {sample_task.is_global}")
    print(f"   is_editable: {sample_task.is_editable}")
    print(f"   is_deletable: {sample_task.is_deletable}")
    print(f"   Status: {sample_task.status}")
    print(f"   Priority: {sample_task.priority}")
    
    # Count by user
    print(f"\n👥 Global tasks per user:")
    for user in users[:5]:
        count = Task.objects.filter(user=user, is_global=True).count()
        print(f"   - {user.username}: {count} tasks")
    
    # Count by category
    print(f"\n📂 Global tasks per category:")
    for cat in global_categories[:5]:
        count = Task.objects.filter(category=cat, is_global=True).count()
        print(f"   - {cat.name}: {count} tasks")
    
    # Verify protection flags
    protected_count = Task.objects.filter(
        is_global=True, 
        is_editable=False, 
        is_deletable=False
    ).count()
    print(f"\n🔒 Protected tasks (not editable/deletable): {protected_count}")
    
    if protected_count == global_tasks.count():
        print("   ✅ All global tasks are properly protected!")
    else:
        print("   ⚠️  Some global tasks may not be properly protected")

else:
    print("\n⚠️  No global tasks found. Run: python manage.py create_global_default_tasks")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
