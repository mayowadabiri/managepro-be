from rest_framework import viewsets
from services.serializers import ServiceSerializer
from rest_framework.permissions import IsAuthenticated
from services.models import Service
from django.db.models import Q


class ServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer

    def get_queryset(self):
       user = self.request.user
       return Service.objects.filter(
           Q(is_predefined=True) | Q(added_by=user)
       )