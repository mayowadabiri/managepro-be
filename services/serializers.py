from rest_framework import serializers
from .models import Service


class ServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "domain",
            "created_at",
            "uuid",
            "is_predefined",
            "image_url",
        ]
