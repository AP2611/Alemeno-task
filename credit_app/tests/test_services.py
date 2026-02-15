"""Unit tests for EMI and eligibility services."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from credit_app.models import Customer, Loan
from credit_app.serializers import approved_limit_from_salary
from credit_app.services.emi import calculate_emi
from credit_app.services.eligibility import check_eligibility, compute_credit_score


class EMICalculatorTests(TestCase):
    """Tests for compound-interest EMI calculation."""

    def test_emi_positive_rate_and_tenure(self):
        emi = calculate_emi(loan_amount=100_000, annual_interest_rate=12, tenure_months=12)
        self.assertGreater(emi, 0)
        self.assertAlmostEqual(emi, 8884.88, places=1)

    def test_emi_zero_tenure_returns_zero(self):
        self.assertEqual(calculate_emi(100_000, 10, 0), 0.0)
        self.assertEqual(calculate_emi(100_000, 10, -1), 0.0)

    def test_emi_zero_interest_is_principal_over_tenure(self):
        emi = calculate_emi(loan_amount=120_000, annual_interest_rate=0, tenure_months=12)
        self.assertEqual(emi, 10_000.0)

    def test_emi_returns_rounded_two_decimals(self):
        emi = calculate_emi(50_000, 15, 6)
        self.assertEqual(round(emi, 2), emi)


class ApprovedLimitTests(TestCase):
    """Tests for approved_limit_from_salary (nearest lakh)."""

    def test_rounds_to_nearest_lakh(self):
        self.assertEqual(approved_limit_from_salary(50_000), round(36 * 50_000 / 100_000) * 100_000)
        self.assertEqual(approved_limit_from_salary(25_000), 900_000)


class EligibilityTests(TestCase):
    """Tests for credit score and check_eligibility."""

    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            phone_number="9999999999",
            monthly_salary=100_000,
            approved_limit=3_600_000,
            current_debt=0,
            age=30,
        )

    def test_customer_not_found_returns_not_approved(self):
        result = check_eligibility(customer_id=99999, loan_amount=100_000, interest_rate=15, tenure=12)
        self.assertFalse(result.approval)
        self.assertIn("not found", result.message.lower())

    def test_high_credit_score_approves_with_any_rate(self):
        # Two loans this year, fully paid on time + volume -> score > 50, so any rate approved
        this_year = date.today().year
        for i, loan_id in enumerate([801, 802]):
            Loan.objects.create(
                customer=self.customer,
                loan_id=loan_id,
                loan_amount=Decimal("200000"),
                tenure=12,
                interest_rate=Decimal("12"),
                monthly_repayment=Decimal("17770"),
                emis_paid_on_time=12,
                emis_paid=12,
                start_date=date(this_year, 1, 1),
                end_date=date(this_year, 12, 31),
            )
        result = check_eligibility(
            customer_id=self.customer.pk,
            loan_amount=100_000,
            interest_rate=10,
            tenure=12,
        )
        self.assertTrue(result.approval)
        self.assertEqual(result.corrected_interest_rate, 10)
        self.assertGreater(result.monthly_installment, 0)

    def test_emi_over_50_percent_salary_rejected(self):
        Loan.objects.create(
            customer=self.customer,
            loan_amount=5_000_000,
            tenure=60,
            interest_rate=12,
            monthly_repayment=111_000,
            emis_paid=0,
        )
        result = check_eligibility(
            customer_id=self.customer.pk,
            loan_amount=200_000,
            interest_rate=15,
            tenure=12,
        )
        self.assertFalse(result.approval)
        self.assertIn("50%", result.message)

    def test_current_loans_over_approved_limit_zero_credit_score(self):
        Loan.objects.create(
            customer=self.customer,
            loan_id=901,
            loan_amount=4_000_000,
            tenure=24,
            interest_rate=12,
            monthly_repayment=188_000,
            emis_paid=0,
        )
        score = compute_credit_score(self.customer)
        self.assertEqual(score, 0.0)
