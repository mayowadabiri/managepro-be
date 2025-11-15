from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid
import secrets
from django.utils import timezone
from datetime import timedelta


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
    password = models.CharField(max_length=128, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    notify_days_before = models.PositiveIntegerField(default=7)
    provider = models.CharField(max_length=256, blank=True, null=True, default="local")
    provider_id = models.CharField(max_length=256, blank=True, null=True)
    image_url = models.ImageField(
        blank=True,
        null=True,
        upload_to=user_image_path,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def generate_user_code(self):
        expires_at = timezone.now() + timedelta(minutes=15)
        code = Code.objects.create(
            user=self, code=Code().generate_code(), expires_at=expires_at
        )
        return code


class Code(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)

    def generate_code(self, length=6):
        """
        Generate a numeric 6-digit OTP code.
        Always zero padded to match length
        """
        otp = secrets.randbelow(10**length)

        return str(otp).zfill(length)
