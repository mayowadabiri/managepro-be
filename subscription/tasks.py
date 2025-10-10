from celery import shared_task
from .models import Subscription, SubscriptionStatus, BillingCycle
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db.models import ExpressionWrapper, F, DurationField, Value


@shared_task
def to_expire_subscription_status_change():
    today = timezone.now().date()

    to_expires_subs = (
        Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE, next_billing_date__isnull=False
        )
        .annotate(
            days_diff=ExpressionWrapper(
                F("next_billing_date") - Value(today), output_field=DurationField()
            )
        )
        .filter(days_diff__days=F("user__notify_days_before"))
    )

    for sub in to_expires_subs:
        # Send Notification
        sub.status = SubscriptionStatus.TO_EXPIRE
        sub.save()


@shared_task
def expire_subscription_status_change():
    today = timezone.now().date()
    expired_subs = Subscription.objects.filter(
        status=SubscriptionStatus.TO_EXPIRE,
        next_billing_date__isnull=False,
        next_billing_date=today,
    )

    for sub in expired_subs:
        # Send Notification
        sub.status = SubscriptionStatus.EXPIRED
        billing_cycle = sub.billing_cycle
        if billing_cycle == BillingCycle.MONTHLY:
            sub.next_billing_date += relativedelta(months=1)
        elif billing_cycle == BillingCycle.QUARTELY:
            sub.next_billing_date += relativedelta(months=3)
        elif billing_cycle == BillingCycle.YEARLY:
            sub.next_billing_date += relativedelta(years=1)
        sub.status = SubscriptionStatus.ACTIVE
        sub.start_date = today
        sub.save()
