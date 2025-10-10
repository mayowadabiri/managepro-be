from django.core.management import BaseCommand

from services.models import Service


from services.constant import SERVICES_DATA


class Command(BaseCommand):
    help = "Populate the Service model with initial data"

    def handle(self, *args, **options):
        for service in SERVICES_DATA:
            obj, created = Service.objects.get_or_create(
                name=service["name"], is_predefined=True, domain=service["link"]
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Added {service['name']}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"{service['name']} already exists")
                )
