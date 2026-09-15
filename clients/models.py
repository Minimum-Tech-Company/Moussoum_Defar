from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    """Client profile (company/startup)."""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=200)
    company_description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    monthly_evaluations = models.IntegerField(default=0)
    max_evaluations = models.IntegerField(default=5)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.get_plan_display()})"

    @property
    def can_evaluate(self):
        return self.monthly_evaluations < self.max_evaluations


class Subscription(models.Model):
    """Client subscription."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('past_due', 'Past Due'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=20, choices=Client.PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_evaluations = models.IntegerField()
    max_api_calls = models.IntegerField(default=10000)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.company_name} - {self.get_plan_display()}"

    @property
    def is_active(self):
        from django.utils import timezone
        return self.status == 'active' and self.ends_at and self.ends_at > timezone.now()
