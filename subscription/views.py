from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from .serializer import SubscriptionSerializer
from .models import Subscription, Category, SubscriptionStatus, BillingCycle
from rest_framework.decorators import action
import django_filters
from django.db.models import Sum, F, Q
from rest_framework.response import Response
from django.utils import timezone
from django.db.models.functions import ExtractMonth
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q, Value
from django.db.models.functions import ExtractMonth, Coalesce
from rest_framework.decorators import action
from rest_framework.response import Response


class SubscriptionFilter(django_filters.FilterSet):

    start_date = django_filters.DateFromToRangeFilter()
    amount = django_filters.RangeFilter()
    category = django_filters.ModelMultipleChoiceFilter(
        field_name="category_id", queryset=Category.objects.all()
    )
    service_name = django_filters.CharFilter(
        field_name="service_id__name", lookup_expr="icontains"
    )

    class Meta:
        model = Subscription
        fields = ["status", "currency", "billing_cycle", "service_name"]


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

    def get_category_breakdown(self, user):
        today = timezone.localdate()
        qs = (
            self.queryset.filter(
                status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TO_EXPIRE],
            )
            .annotate(this_month=ExtractMonth("start_date"))
            .filter(
                this_month=today.month,
            )
            .values(name=F("category_id__name"))
            .annotate(total=Coalesce(Sum("amount"), Value(Decimal("0.00"))))
        )

        return list(qs)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = self.get_queryset()  # assume this is already user-scoped
        today = timezone.localdate()

        status_filter = Q(status=SubscriptionStatus.ACTIVE) | Q(
            status=SubscriptionStatus.TO_EXPIRE
        )

        monthly_base = qs.filter(
            status_filter,
            billing_cycle="monthly",
        ).exclude(next_billing_date__isnull=True)

        monthly_spending = (
            monthly_base.annotate(next_month=ExtractMonth("start_date"))
            .filter(next_month=today.month)
            .aggregate(total=Coalesce(Sum("amount"), Value(Decimal("0.00"))))["total"]
        )

        monthly_all_sum = qs.filter(
            status_filter, billing_cycle=BillingCycle.MONTHLY
        ).aggregate(total=Coalesce(Sum("amount"), Value(Decimal("0.00"))))["total"]
        projected_year_from_monthly = (monthly_all_sum or Decimal("0.00")) * Decimal(
            "12"
        )

        yearly_direct_sum = qs.filter(
            status_filter, billing_cycle=BillingCycle.YEARLY
        ).aggregate(total=Coalesce(Sum("amount"), Value(Decimal("0.00"))))["total"]

        yearly_spending = (
            yearly_direct_sum or Decimal("0.00")
        ) + projected_year_from_monthly

        renewals = (
            qs.filter(status=SubscriptionStatus.TO_EXPIRE)
            .annotate(next_month=ExtractMonth("next_billing_date"))
            .filter(next_month=today.month)
        )

        category_breakdown = self.get_category_breakdown(request.user)
        print("----------------------_")
        print(category_breakdown)
        print("----------------------_")

        data = {
            "monthly_spending": (monthly_spending),
            "yearly_spending": (yearly_spending),
            "renewals_count": renewals.count(),
            "renewals": renewals,
            "category_breakdown": category_breakdown,
        }

        return Response(data)
