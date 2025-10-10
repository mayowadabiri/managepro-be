from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from .serializer import SubscriptionSerializer
from .models import Subscription, Category, SubscriptionStatus
from rest_framework.decorators import action
import django_filters
from django.db.models import Sum
from rest_framework.response import Response


class SubscriptionFilter(django_filters.FilterSet):

    start_date = django_filters.DateFromToRangeFilter()
    amount = django_filters.RangeFilter()
    category = django_filters.ModelMultipleChoiceFilter(
        field_name="category_ids", queryset=Category.objects.all()
    )
    service_name = django_filters.CharFilter(
        field_name="service_id__name", lookup_expr="icontains"
    )

    class Meta:
        model = Subscription
        fields = ["status", "currency", "billing_cycle", "category", "service_name"]


class SubscriptionViewset(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = SubscriptionFilter

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubscriptionAnalyticsViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Subscription.objects.all()

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = self.get_queryset()
        data = {
            "active_count": qs.filter(status=SubscriptionStatus.ACTIVE).count(),
            "to_expire_count": qs.filter(status=SubscriptionStatus.TO_EXPIRE).count(),
            "total_amount": qs.aggregate(Sum("amount"))["amount__sum"] or 0,
        }

        return Response({"message": "Retrieved Successfully", "data": data})
