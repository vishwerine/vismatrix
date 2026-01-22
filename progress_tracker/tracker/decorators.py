"""
Custom decorators for input validation and rate limiting
"""
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import redirect
import time
import logging

logger = logging.getLogger(__name__)


def rate_limit(requests_per_minute=30, key_prefix='rate_limit'):
    """
    Rate limiting decorator for views.
    
    Args:
        requests_per_minute: Maximum number of requests allowed per minute
        key_prefix: Prefix for cache key
    
    Usage:
        @rate_limit(requests_per_minute=10)
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Build cache key from user ID and view name
            user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')
            cache_key = f"{key_prefix}:{func.__name__}:{user_id}"
            
            # Get request history from cache
            request_times = cache.get(cache_key, [])
            now = time.time()
            
            # Remove old requests (older than 1 minute)
            request_times = [t for t in request_times if now - t < 60]
            
            # Check if rate limit exceeded
            if len(request_times) >= requests_per_minute:
                logger.warning(f"Rate limit exceeded for user {user_id} on {func.__name__}")
                
                # Return appropriate response based on request type
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Rate limit exceeded. Please slow down.',
                        'status': 'error'
                    }, status=429)
                else:
                    messages.error(request, 'You are making requests too quickly. Please slow down.')
                    return redirect('dashboard')
            
            # Add current request time
            request_times.append(now)
            cache.set(cache_key, request_times, 60)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def validate_ajax(func):
    """
    Decorator to ensure request is AJAX.
    Returns 400 error if not an AJAX request.
    
    Usage:
        @validate_ajax
        def my_ajax_view(request):
            ...
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'This endpoint only accepts AJAX requests',
                'status': 'error'
            }, status=400)
        return func(request, *args, **kwargs)
    
    return wrapper


def validate_json(required_fields=None):
    """
    Decorator to validate JSON request body and required fields.
    
    Args:
        required_fields: List of required field names in JSON body
    
    Usage:
        @validate_json(required_fields=['username', 'email'])
        def my_view(request):
            data = request.json_data  # Parsed JSON data
            ...
    """
    if required_fields is None:
        required_fields = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Parse JSON body
            try:
                import json
                if not request.body:
                    return JsonResponse({
                        'error': 'Empty request body',
                        'status': 'error'
                    }, status=400)
                    
                data = json.loads(request.body.decode('utf-8'))
                request.json_data = data  # Attach parsed data to request
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'Invalid JSON in request body',
                    'status': 'error'
                }, status=400)
            except Exception as e:
                logger.error(f"Error parsing JSON: {str(e)}")
                return JsonResponse({
                    'error': 'Error parsing request',
                    'status': 'error'
                }, status=400)
            
            # Validate required fields
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse({
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'status': 'error'
                }, status=400)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def log_errors(func):
    """
    Decorator to log errors that occur in views.
    
    Usage:
        @log_errors
        def my_view(request):
            ...
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error in {func.__name__} for user {request.user.id if request.user.is_authenticated else 'anonymous'}: {str(e)}",
                exc_info=True
            )
            
            # Return appropriate error response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'An unexpected error occurred. Please try again.',
                    'status': 'error'
                }, status=500)
            else:
                messages.error(request, 'An unexpected error occurred. Please try again.')
                return redirect('dashboard')
    
    return wrapper


def require_ownership(model_class, param_name='pk', owner_field='user'):
    """
    Decorator to verify that the logged-in user owns the object being accessed.
    
    Args:
        model_class: The model class to check
        param_name: Name of URL parameter containing object ID
        owner_field: Name of field that contains the owner (default: 'user')
    
    Usage:
        @require_ownership(Task, param_name='task_id')
        def edit_task(request, task_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from django.shortcuts import get_object_or_404
            
            # Get object ID from kwargs
            obj_id = kwargs.get(param_name)
            if not obj_id:
                return JsonResponse({
                    'error': 'Object ID not provided',
                    'status': 'error'
                }, status=400)
            
            # Get object and verify ownership
            obj = get_object_or_404(model_class, pk=obj_id)
            
            # Check ownership
            owner = getattr(obj, owner_field, None)
            if owner != request.user:
                logger.warning(
                    f"Unauthorized access attempt: User {request.user.id} "
                    f"tried to access {model_class.__name__} {obj_id}"
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'You do not have permission to access this resource',
                        'status': 'error'
                    }, status=403)
                else:
                    messages.error(request, 'You do not have permission to access this resource.')
                    return redirect('dashboard')
            
            # Attach object to request for use in view
            request.verified_object = obj
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def pro_required(redirect_url='subscription_plans'):
    """
    Decorator to require Pro subscription for accessing a view.
    
    Usage:
        @login_required
        @pro_required()
        def advanced_feature(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from .models import Subscription
            
            # Check if user has active pro subscription
            try:
                subscription = request.user.subscription
                if subscription.is_pro:
                    return func(request, *args, **kwargs)
            except Subscription.DoesNotExist:
                # Create free subscription if doesn't exist
                Subscription.objects.create(
                    user=request.user,
                    plan='free',
                    status='active'
                )
            
            # User doesn't have pro access
            messages.warning(
                request,
                '⭐ This is a Pro feature. Upgrade to VisMatrix Pro to unlock advanced features!'
            )
            return redirect(redirect_url)
        
        return wrapper
    return decorator

