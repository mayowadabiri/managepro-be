from django.db import models
from user.models import User
from services.models import Service
import uuid
from django.utils import timezone


CURRENCY_CHOICES = [
    ("NGN", "Naira"),
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("GBP", "British Pound"),
]


class BillingCycle(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"
    QUARTELY = "quarterly", "Quarterly"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    TO_EXPIRE = "to_expire", "To Expire"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


class Category(models.Model):
    name = models.CharField(max_length=256)
    created_at = models.DateField(auto_now_add=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    is_predefined = models.BooleanField(default=False)


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    service_id = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=4, choices=CURRENCY_CHOICES)
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
    )
    start_date = models.DateField()
    next_billing_date = models.DateField()
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    trial_start_date = models.DateField(blank=True, null=True)
    trial_end_date = models.DateField(blank=True, null=True)
    trial_billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    is_trial = models.BooleanField(default=False)
    category_id = models.ForeignKey(
        Category,
        blank=True,
        related_name="subscriptions",
        on_delete=models.CASCADE,
        default=None,
        null=True,
    )

    @property
    def get_trial_end_day(self):
        """
        Returns the number of days remaining until the trial ends.
        If expired, returns 0.
        """
        if not self.trial_end_date:
            return 0
        today = timezone.now().date()
        delta = self.trial_end_date - today
        return max(delta, 0)
