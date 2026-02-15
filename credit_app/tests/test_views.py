"""API tests for credit_app endpoints."""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from credit_app.models import Customer, Loan


class RegisterAPITests(TestCase):
    client_class = APIClient

    def test_register_creates_customer_returns_201(self):
        response = self.client.post(
            "/register",
            {
                "first_name": "New",
                "last_name": "User",
                "age": 28,
                "monthly_income": 60000,
                "phone_number": 9876543210,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("customer_id", data)
        self.assertEqual(data["name"], "New User")
        self.assertEqual(data["age"], 28)
        self.assertEqual(data["monthly_income"], 60000)
        self.assertEqual(data["approved_limit"], 2200000)

    def test_register_invalid_returns_400(self):
        response = self.client.post(
            "/register",
            {"first_name": "", "last_name": "X", "age": 150, "monthly_income": -1, "phone_number": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("first_name", data)
        self.assertIn("age", data)


class CheckEligibilityAPITests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Elig",
            last_name="Test",
            phone_number="9999888777",
            monthly_salary=80_000,
            approved_limit=2_900_000,
            current_debt=0,
            age=35,
        )

    def test_check_eligibility_returns_200(self):
        response = self.client.post(
            "/check-eligibility",
            {
                "customer_id": self.customer.pk,
                "loan_amount": 100000,
                "interest_rate": 14,
                "tenure": 12,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["customer_id"], self.customer.pk)
        self.assertIn("approval", data)
        self.assertIn("corrected_interest_rate", data)
        self.assertIn("monthly_installment", data)
        self.assertEqual(data["tenure"], 12)


class CreateLoanAPITests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Loan",
            last_name="User",
            phone_number="8888777766",
            monthly_salary=100_000,
            approved_limit=3_600_000,
            current_debt=0,
            age=40,
        )

    def test_create_loan_approved_returns_201(self):
        response = self.client.post(
            "/create-loan",
            {
                "customer_id": self.customer.pk,
                "loan_amount": 50_000,
                "interest_rate": 14,
                "tenure": 12,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["loan_approved"])
        self.assertIsNotNone(data["loan_id"])
        self.assertGreater(data["monthly_installment"], 0)

    def test_create_loan_rejected_returns_200_with_message(self):
        response = self.client.post(
            "/create-loan",
            {
                "customer_id": self.customer.pk,
                "loan_amount": 500_000,
                "interest_rate": 8,
                "tenure": 12,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["loan_approved"])
        self.assertIsNone(data["loan_id"])
        self.assertIn("message", data)


class ViewLoanAPITests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="View",
            last_name="Customer",
            phone_number="7777666655",
            monthly_salary=50_000,
            approved_limit=1_800_000,
            current_debt=0,
            age=28,
        )
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_id=1001,
            loan_amount=Decimal("100000.00"),
            tenure=24,
            interest_rate=Decimal("12.00"),
            monthly_repayment=Decimal("4707.35"),
            emis_paid=0,
        )

    def test_view_loan_returns_200(self):
        response = self.client.get(f"/view-loan/{self.loan.pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["loan_id"], self.loan.loan_id or self.loan.pk)
        self.assertEqual(data["loan_amount"], "100000.00")
        self.assertIn("customer", data)
        self.assertEqual(data["customer"]["first_name"], "View")

    def test_view_loan_not_found_returns_404(self):
        response = self.client.get("/view-loan/99999999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ViewLoansAPITests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="List",
            last_name="User",
            phone_number="6666555544",
            monthly_salary=60_000,
            approved_limit=2_200_000,
            current_debt=0,
            age=32,
        )

    def test_view_loans_returns_200_and_list(self):
        response = self.client.get(f"/view-loans/{self.customer.pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), list)

    def test_view_loans_customer_not_found_returns_404(self):
        response = self.client.get("/view-loans/99999999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.json().get("detail", "").lower())
