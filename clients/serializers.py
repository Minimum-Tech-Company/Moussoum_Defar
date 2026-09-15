from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Client, Subscription


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    plan_display = serializers.CharField(source='get_plan_display', read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'user', 'company_name', 'company_description',
            'website', 'plan', 'plan_display', 'monthly_evaluations',
            'max_evaluations', 'is_verified', 'created_at', 'updated_at'
        ]


class ClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['company_name', 'company_description', 'website']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_display = serializers.CharField(source='get_plan_display', read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'client', 'plan', 'plan_display', 'status',
            'monthly_price', 'max_evaluations', 'max_api_calls',
            'starts_at', 'ends_at', 'is_active', 'created_at'
        ]
        read_only_fields = ['client', 'status', 'starts_at']
