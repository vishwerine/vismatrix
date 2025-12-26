from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Task, DailyLog, Category, DailySummary, FriendRequest, Friendship, Plan, PlanNode


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'user', 'title', 'description', 'status', 'priority', 
                  'due_date', 'category', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class DailyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = ['id', 'user', 'date', 'activity', 'category', 'duration', 
                  'description', 'task', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'user', 'name', 'color', 'is_global', 'created_at']
        read_only_fields = ['id', 'user', 'is_global', 'created_at']


class DailySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySummary
        fields = ['id', 'user', 'date', 'total_tasks_completed', 'total_time_spent', 
                  'notes', 'productivity_rating']
        read_only_fields = ['id', 'user']


class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    
    class Meta:
        model = FriendRequest
        fields = ['id', 'from_user', 'to_user', 'created_at', 'status']
        read_only_fields = ['id', 'created_at', 'status']


class FriendshipSerializer(serializers.ModelSerializer):
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)
    
    class Meta:
        model = Friendship
        fields = ['id', 'user1', 'user2', 'created_at']
        read_only_fields = ['id', 'created_at']


class PlanNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanNode
        fields = ['id', 'plan', 'title', 'description', 'order', 'parent', 'created_at']
        read_only_fields = ['id', 'created_at']


class PlanSerializer(serializers.ModelSerializer):
    nodes = PlanNodeSerializer(many=True, read_only=True, source='plannode_set')
    
    class Meta:
        model = Plan
        fields = ['id', 'user', 'title', 'description', 'created_at', 'updated_at', 'nodes']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
