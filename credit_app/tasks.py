import logging
from datetime import datetime
from decimal import Decimal

import pandas as pd
from celery import shared_task
from django.conf import settings
from django.db import connection

from .models import Customer, Loan


def _reset_customer_sequence():
    """Reset Customer id sequence so new registrations don't conflict with ingested IDs."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('credit_app_customer', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM credit_app_customer));"
        )

logger = logging.getLogger(__name__)


@shared_task
def ingest_customers_from_excel(file_path: str) -> dict:
    """Read customer_data.xlsx and upsert into Customer table."""
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        logger.exception("Failed to read customer Excel: %s", file_path)
        return {'ok': False, 'error': str(e), 'created': 0, 'updated': 0}

    # Normalize column names: lowercase, strip, replace spaces with underscore
    df.columns = [
        str(c).strip().lower().replace(' ', '_') if isinstance(c, str) else c
        for c in df.columns
    ]
    created = updated = 0
    for _, row in df.iterrows():
        try:
            customer_id = int(row.get('customer_id', 0))
            monthly_salary = int(row.get('monthly_salary', 0))
            approved_limit = int(row.get('approved_limit', 0))
            current_debt = int(row.get('current_debt', 0))
            first_name = str(row.get('first_name', '')).strip()
            last_name = str(row.get('last_name', '')).strip()
            pn = row.get('phone_number')
            phone_number = str(int(pn)) if pd.notna(pn) and str(pn).replace('.', '').isdigit() else (str(pn) if pd.notna(pn) else '0')
            if not first_name and not last_name:
                continue
            obj, was_created = Customer.objects.update_or_create(
                pk=customer_id,
                defaults={
                    'first_name': first_name or 'Unknown',
                    'last_name': last_name or 'Unknown',
                    'phone_number': phone_number,
                    'monthly_salary': monthly_salary,
                    'approved_limit': approved_limit,
                    'current_debt': current_debt,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as e:
            logger.warning("Skip row %s: %s", row.to_dict(), e)
            continue
    _reset_customer_sequence()
    return {'ok': True, 'created': created, 'updated': updated}


def _parse_date(val):
    if val is None or (hasattr(val, '__iter__') and not isinstance(val, str) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date()
    if hasattr(val, 'date'):
        return val.date()
    if isinstance(val, str):
        try:
            return datetime.strptime(val[:10], '%Y-%m-%d').date()
        except Exception:
            pass
    return None


@shared_task
def ingest_loans_from_excel(file_path: str) -> dict:
    """Read loan_data.xlsx and upsert into Loan table."""
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        logger.exception("Failed to read loan Excel: %s", file_path)
        return {'ok': False, 'error': str(e), 'created': 0, 'updated': 0}

    df.columns = [
        str(c).strip().lower().replace(' ', '_') if isinstance(c, str) else c
        for c in df.columns
    ]
    created = updated = 0
    for _, row in df.iterrows():
        try:
            loan_id = int(row.get('loan_id', 0))
            customer_id = int(row.get('customer_id', 0))
            loan_amount = Decimal(str(row.get('loan_amount', 0)))
            tenure = int(row.get('tenure', 0))
            interest_rate = Decimal(str(row.get('interest_rate', 0)))
            monthly_repayment = Decimal(str(row.get('monthly_repayment', row.get('emi', 0))))
            emis_paid_on_time = int(row.get('emis_paid_on_time', 0))
            start_date = _parse_date(row.get('start_date'))
            end_date = _parse_date(row.get('end_date'))

            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                logger.warning("Customer %s not found for loan %s", customer_id, loan_id)
                continue

            emis_paid = min(tenure, int(row.get('emis_paid', emis_paid_on_time)))

            obj, was_created = Loan.objects.update_or_create(
                loan_id=loan_id,
                defaults={
                    'customer': customer,
                    'loan_amount': loan_amount,
                    'tenure': tenure,
                    'interest_rate': interest_rate,
                    'monthly_repayment': monthly_repayment,
                    'emis_paid_on_time': emis_paid_on_time,
                    'emis_paid': emis_paid,
                    'start_date': start_date,
                    'end_date': end_date,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as e:
            logger.warning("Skip loan row %s: %s", row.to_dict(), e)
            continue
    return {'ok': True, 'created': created, 'updated': updated}
