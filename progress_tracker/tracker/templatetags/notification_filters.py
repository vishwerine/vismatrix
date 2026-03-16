from django import template

register = template.Library()

@register.filter(name='has_timer_url')
def has_timer_url(message):
    """Check if message contains a timer URL"""
    return '|||' in message

@register.filter(name='get_timer_text')
def get_timer_text(message):
    """Extract just the text part from timer message"""
    if '|||' in message:
        return message.split('|||')[0].strip()
    return message

@register.filter(name='get_timer_url')
def get_timer_url(message):
    """Extract just the URL part from timer message"""
    if '|||' in message:
        parts = message.split('|||')
        if len(parts) > 1:
            return parts[1].strip()
    return ''
