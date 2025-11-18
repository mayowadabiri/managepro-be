import hmac, hashlib
from django.conf import settings


def hash_otp(code: str) -> str:
    return hmac.new(
        key=settings.OTP_SECRET_KEY.encode(),
        msg=str(code).encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
