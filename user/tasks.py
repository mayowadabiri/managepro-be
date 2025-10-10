from celery import shared_task
from user.models import Code
from django.utils import timezone
from dateutil.relativedelta import relativedelta


@shared_task
def clear_used_otp():
    today = timezone.now().date()
    one_month_ago = today - relativedelta(months=1)

    Code.objects.filter(is_used=True, created_at__date=one_month_ago).delete()
