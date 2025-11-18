import resend
from django.conf import settings


resend.api_key = settings.RESEND_API_KEY


def send_email(to, variables):
    resend.Emails.send(
        {"from": settings.RESEND_EMAIL_FROM, "to": to, "template": {**variables}}
    )
