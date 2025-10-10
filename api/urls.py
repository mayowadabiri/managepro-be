from rest_framework.routers import DefaultRouter
from user.views import AuthViewset, UserViewSet
from django.urls import path, include
from services.views import ServiceViewSet
from subscription.views import SubscriptionViewset, SubscriptionAnalyticsViewSet


router = DefaultRouter(trailing_slash=False)
router.register(r"auth", AuthViewset, basename="auth")
router.register(r"user", UserViewSet, basename="user")
router.register(r"service", ServiceViewSet, basename="service")
router.register(r"subscription", SubscriptionViewset, basename="subscription")
router.register(r"analytics", SubscriptionAnalyticsViewSet, basename="analysis")

urlpatterns = [
    path("", include(router.urls)),
]
