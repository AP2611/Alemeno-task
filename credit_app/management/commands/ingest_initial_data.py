import os

from django.conf import settings
from django.core.management.base import BaseCommand

from credit_app.tasks import ingest_customers_from_excel, ingest_loans_from_excel


class Command(BaseCommand):
    help = 'Enqueue Celery tasks to ingest customer_data.xlsx and loan_data.xlsx'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run ingestion synchronously instead of via Celery',
        )

    def handle(self, *args, **options):
        customer_path = getattr(settings, 'CUSTOMER_DATA_PATH', None) or os.path.join(
            settings.BASE_DIR, 'data', 'customer_data.xlsx'
        )
        loan_path = getattr(settings, 'LOAN_DATA_PATH', None) or os.path.join(
            settings.BASE_DIR, 'data', 'loan_data.xlsx'
        )

        if not os.path.isfile(customer_path):
            self.stdout.write(self.style.WARNING(
                f'Customer file not found: {customer_path}. Place customer_data.xlsx in data/ and retry.'
            ))
        if not os.path.isfile(loan_path):
            self.stdout.write(self.style.WARNING(
                f'Loan file not found: {loan_path}. Place loan_data.xlsx in data/ and retry.'
            ))

        if options['sync']:
            self.stdout.write('Running ingestion synchronously...')
            r1 = ingest_customers_from_excel(customer_path)
            self.stdout.write(f'Customers: {r1}')
            r2 = ingest_loans_from_excel(loan_path)
            self.stdout.write(f'Loans: {r2}')
            self.stdout.write(self.style.SUCCESS('Done.'))
            return

        self.stdout.write('Enqueueing Celery tasks...')
        ingest_customers_from_excel.delay(customer_path)
        ingest_loans_from_excel.delay(loan_path)
        self.stdout.write(self.style.SUCCESS(
            'Tasks enqueued. Ensure Celery worker is running to process them.'
        ))
