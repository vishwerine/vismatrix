from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin


class SaveMessagesMiddleware(MiddlewareMixin):
    """Middleware to save Django messages to database for persistent storage."""
    
    def process_response(self, request, response):
        """Save messages to database after request is processed."""
        # Only process for authenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        
        # Get messages from the request
        storage = messages.get_messages(request)
        if storage:
            from .models import UserNotification
            
            for message in storage:
                # Map Django message levels to our notification levels
                level_map = {
                    messages.SUCCESS: 'success',
                    messages.INFO: 'info',
                    messages.WARNING: 'warning',
                    messages.ERROR: 'error',
                    messages.DEBUG: 'info',
                }
                
                level = level_map.get(message.level, 'info')
                
                # Create notification in database
                UserNotification.objects.create(
                    user=request.user,
                    level=level,
                    message=str(message)
                )
        
        return response
