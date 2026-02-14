from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Reset Customer id sequence so new registrations work after Excel ingestion.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('credit_app_customer', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM credit_app_customer));"
            )
        self.stdout.write(self.style.SUCCESS('Customer id sequence reset.'))
