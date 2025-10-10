from django.core.management import BaseCommand

from subscription.models import Category

from subscription.constants import CATEGORIES


class Command(BaseCommand):
    help = "Populate the Service model with initial data"

    def handle(self, *args, **options):
        for service in CATEGORIES:
            obj, created = Category.objects.get_or_create(
                name=service, is_predefined=True
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Added {service}"))
            else:
                self.stdout.write(self.style.WARNING(f"{service} already exists"))
