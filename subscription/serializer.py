from rest_framework import serializers

from .models import Subscription, Category
from services.serializers import ServiceSerializer
from services.models import Service


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name", "id"]


class SubscriptionSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), required=False, write_only=True
    )
    days_left = serializers.ReadOnlyField(source="get_days_left")
    service = ServiceSerializer(source="service_id", read_only=True)
    service_name = serializers.CharField(write_only=True, required=False)
    service_logo = serializers.FileField(write_only=True, required=False)
    category = CategorySerializer(source="category_id", read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Subscription
        read_only_fields = [
            "id",
            "user",
            "service_id",
            "days_left",
            "uuid",
            "service",
        ]
        fields = [
            "amount",
            "currency",
            "billing_cycle",
            "status",
            "start_date",
            "next_billing_date",
            "trial_end_date",
            "trial_start_date",
            "is_trial",
            "service_name",
            "service_logo",
            "category",
            "category_id",
        ] + read_only_fields

    def create(self, validated_data):
        print(validated_data)
        service_name = validated_data.pop("service_name", None)
        service_id = validated_data.pop("service_id", None)
        if service_name:
            file = self.context["request"].FILES.get("service_logo", None)
            service_details = {
                "name": service_name,
                "logo": file,
                "domain": validated_data.pop("domain", None),
            }
            service = Service.create_new_service(
                service_details=service_details, user=self.context["request"].user
            )
            validated_data.pop("service_logo", None)
        elif service_id:
            service = service_id
        else:
            raise serializers.ValidationError(
                "You must provide either a service id or service name"
            )

        subscription = Subscription.objects.create(service_id=service, **validated_data)

        return subscription
