
from tracker.models import Conversation, ConversationMember, Message, Friendship

from django.contrib.auth.models import User


def are_friends(user_a: User, user_b: User) -> bool:
    return Friendship.objects.filter(user=user_a, friend=user_b).exists()
