from rest_framework import serializers
from .models import User
from django.contrib.auth.hashers import make_password


class UserSerializers(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "uuid",
            "password",
            "is_verified",
            "notify_days_before",
        ]
        read_only_fields = [
            "id",
            "uuid",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": True},
            "email": {"validators": []},
        }

    def to_internal_value(self, data):
        data = data.copy()
        data.pop("confirmPassword", None)
        return super().to_internal_value(data)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "This email already exists. Please use a different email."
            )
        return value

    def create(self, validated_data):
        password = validated_data["password"]
        validated_data["password"] = make_password(password)
        user = super().create(validated_data)
        return user
