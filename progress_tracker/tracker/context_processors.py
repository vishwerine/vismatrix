from .models import FriendRequest

def pending_friend_requests_count(request):
    if not request.user.is_authenticated:
        return {'pending_friend_requests_count': 0}
    count = FriendRequest.objects.filter(to_user=request.user, status='pending').count()
    return {'pending_friend_requests_count': count}
