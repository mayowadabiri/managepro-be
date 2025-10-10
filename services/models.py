from django.db import models
from user.models import User
from uuid import uuid4


def service_image_path(instance, filename):
    ext = filename.split(".")[-1]

    new_filename = f"{instance.name}-{instance.uuid}.{ext}"

    return f"logo/{new_filename}"


class Service(models.Model):
    name = models.CharField(max_length=256)

    image_url = models.ImageField(
        blank=True,
        null=True,
        upload_to=service_image_path,
    )

    is_predefined = models.BooleanField(default=False)

    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    domain = models.URLField(null=True, max_length=256)

    created_at = models.DateTimeField(auto_now_add=True)

    uuid = models.UUIDField(default=uuid4, editable=False)

    @classmethod
    def create_new_service(cls, service_details, user):
        service = cls(
            name=service_details.get("name"), is_predefined=False, added_by=user
        )
        domain = service_details.get("domain", None)
        if domain:
            service.domain = domain

        logo = service_details.get("logo", None)

        if logo:
            service.image_url.save(logo.name, logo, save=False)

        service.save()
        return service
