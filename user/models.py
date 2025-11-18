from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid
import secrets
from django.utils import timezone
from datetime import timedelta
from core.secrets import hash_otp


def user_image_path(instance, filename):
    ext = filename.split(".")[-1]

    new_filename = f"{instance.name}-{instance.uuid}.{ext}"

    return f"{instance.uuid}/{new_filename}"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


# Create your models here.
class User(AbstractUser):
    username = None
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(blank=False, unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    password = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    notify_days_before = models.PositiveIntegerField(default=7)
    image_url = models.URLField(
        blank=True,
        null=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def generate_user_code(self):
        """
        Generate a numeric 6-digit OTP code.
        Always zero padded to match length
        """
        expires_at = timezone.now() + timedelta(minutes=15)
        code = secrets.randbelow(10**6)
        paadded_code = str(code).zfill(6)
        hashed_code = hash_otp(paadded_code)
        Code.objects.create(user=self, code_hash=hashed_code, expires_at=expires_at)
        return paadded_code


class Type(models.TextChoices):
    REGISTRATION = "registration"
    FORGOT_PASSWORD = "forgot_password"


class Code(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_code")
    code_hash = models.CharField(max_length=255, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    type = models.CharField(
        max_length=30, choices=Type.choices, default=Type.REGISTRATION
    )
    attempts = models.IntegerField(default=0)


class UserProvider(models.Model):
    provider = models.CharField(max_length=256, blank=True, null=True, default="local")
    provider_id = models.CharField(max_length=256, blank=True, null=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_provider"
    )
    provider_email = models.CharField(max_length=256)
    linked_at = models.DateTimeField(auto_now=True)
