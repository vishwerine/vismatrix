# myapp/templatetags/friends_extras.py
from django import template

register = template.Library()

@register.filter
def sum_total_tasks(friends_data):
    return sum(data.completed_tasks for data in friends_data)

@register.filter
def sum_total_time(friends_data):
    return sum(data.total_time for data in friends_data)