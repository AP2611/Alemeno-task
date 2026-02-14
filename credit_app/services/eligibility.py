"""
Credit score (0-100) and loan approval logic.
Weights: 40% on-time, 20% number of loans, 20% current-year activity, 20% volume.
"""
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from django.db.models import F, Sum

from credit_app.models import Customer, Loan
from credit_app.services.emi import calculate_emi


# Slab minimum rates by credit score band (lowest rate that can be approved)
SLAB_MIN_RATE_30_50 = Decimal('12')
SLAB_MIN_RATE_10_30 = Decimal('16')


class EligibilityResult(NamedTuple):
    approval: bool
    corrected_interest_rate: float
    monthly_installment: float
    message: str = ''


def get_current_loans_queryset(customer_id: int):
    """Loans not yet fully repaid (emis_paid < tenure)."""
    return Loan.objects.filter(customer_id=customer_id).filter(emis_paid__lt=F('tenure'))


def compute_credit_score(customer: Customer) -> float:
    """
    Credit score 0-100 from:
    1. Past loans paid on time (40%)
    2. Number of loans in past (20%)
    3. Loan activity in current year (20%)
    4. Loan approved volume (20%)
    5. If sum of current loan principals > approved_limit -> 0
    """
    current_loans = Loan.objects.filter(customer=customer).filter(emis_paid__lt=F('tenure'))
    total_current_principal = current_loans.aggregate(s=Sum('loan_amount'))['s']
    if total_current_principal is not None and float(total_current_principal) > customer.approved_limit:
        return 0.0

    all_loans = Loan.objects.filter(customer=customer)
    total_emis_due = sum(max(0, loan.tenure) for loan in all_loans)
    total_emis_on_time = sum(loan.emis_paid_on_time for loan in all_loans)
    on_time_ratio = (total_emis_on_time / total_emis_due) if total_emis_due else 1.0
    on_time_score = min(100, on_time_ratio * 100)

    num_loans = all_loans.count()
    loans_score = min(100, num_loans * 10)

    current_year = date.today().year
    current_year_loans = all_loans.filter(start_date__year=current_year)
    cy_count = current_year_loans.count()
    activity_score = min(100, cy_count * 25)

    total_volume = all_loans.aggregate(s=Sum('loan_amount'))['s']
    volume_score = min(100, float(total_volume or 0) / 100000)

    score = 0.4 * on_time_score + 0.2 * loans_score + 0.2 * activity_score + 0.2 * volume_score
    return min(100.0, max(0.0, score))


def check_eligibility(
    customer_id: int,
    loan_amount: float,
    interest_rate: float,
    tenure: int,
) -> EligibilityResult:
    """
    Returns approval, corrected_interest_rate, monthly_installment, and optional message.
    """
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return EligibilityResult(False, interest_rate, 0.0, 'Customer not found')

    credit_score = compute_credit_score(customer)

    current_loans = get_current_loans_queryset(customer_id)
    current_emis_sum = current_loans.aggregate(s=Sum('monthly_repayment'))['s'] or 0
    new_emi = calculate_emi(loan_amount, interest_rate, tenure)
    total_emi_after = float(current_emis_sum) + new_emi
    if total_emi_after > 0.5 * customer.monthly_salary:
        return EligibilityResult(
            False, interest_rate,
            round(new_emi, 2),
            'Sum of current EMIs and new EMI exceeds 50% of monthly salary'
        )

    if credit_score <= 10:
        return EligibilityResult(
            False, interest_rate, round(new_emi, 2),
            'Credit score too low (<=10)'
        )

    rate_decimal = Decimal(str(interest_rate))
    corrected = float(rate_decimal)

    if credit_score <= 30:
        if rate_decimal <= SLAB_MIN_RATE_10_30:
            return EligibilityResult(
                False, interest_rate, round(new_emi, 2),
                'Interest rate must be > 16% for this credit score'
            )
        corrected = max(float(rate_decimal), float(SLAB_MIN_RATE_10_30))
    elif credit_score <= 50:
        if rate_decimal <= SLAB_MIN_RATE_30_50:
            return EligibilityResult(
                False, interest_rate, round(new_emi, 2),
                'Interest rate must be > 12% for this credit score'
            )
        corrected = max(float(rate_decimal), float(SLAB_MIN_RATE_30_50))
    # else credit_score > 50: any rate, corrected = interest_rate

    monthly = calculate_emi(loan_amount, corrected, tenure)
    return EligibilityResult(True, corrected, round(monthly, 2))
