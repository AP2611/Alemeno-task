"""
Compound-interest monthly installment (EMI) calculation.
EMI = P * r * (1+r)^n / ((1+r)^n - 1)
where r = annual_rate / (12 * 100), P = principal, n = tenure in months.
"""
from decimal import Decimal


def calculate_emi(loan_amount: float, annual_interest_rate: float, tenure_months: int) -> float:
    """Return monthly EMI. Uses compound interest formula."""
    if tenure_months <= 0:
        return 0.0
    if annual_interest_rate <= 0:
        return float(loan_amount) / tenure_months
    p = float(loan_amount)
    r = float(annual_interest_rate) / (12 * 100)
    n = int(tenure_months)
    factor = (1 + r) ** n
    emi = p * r * factor / (factor - 1)
    return round(emi, 2)
