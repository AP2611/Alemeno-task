from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer, Loan
from .serializers import (
    CheckEligibilitySerializer,
    CreateLoanSerializer,
    LoanDetailSerializer,
    LoanListItemSerializer,
    RegisterSerializer,
)
from .services.eligibility import check_eligibility


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        customer = serializer.save()
        return Response(
            {
                'customer_id': customer.pk,
                'name': customer.full_name,
                'age': customer.age,
                'monthly_income': customer.monthly_salary,
                'approved_limit': customer.approved_limit,
                'phone_number': int(customer.phone_number) if customer.phone_number.isdigit() else customer.phone_number,
            },
            status=status.HTTP_201_CREATED,
        )


class CheckEligibilityView(APIView):
    def post(self, request):
        serializer = CheckEligibilitySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        result = check_eligibility(
            customer_id=data['customer_id'],
            loan_amount=float(data['loan_amount']),
            interest_rate=float(data['interest_rate']),
            tenure=data['tenure'],
        )
        return Response(
            {
                'customer_id': data['customer_id'],
                'approval': result.approval,
                'interest_rate': float(data['interest_rate']),
                'corrected_interest_rate': result.corrected_interest_rate,
                'tenure': data['tenure'],
                'monthly_installment': result.monthly_installment,
            },
            status=status.HTTP_200_OK,
        )


class CreateLoanView(APIView):
    def post(self, request):
        serializer = CreateLoanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        result = check_eligibility(
            customer_id=data['customer_id'],
            loan_amount=float(data['loan_amount']),
            interest_rate=float(data['interest_rate']),
            tenure=data['tenure'],
        )
        if not result.approval:
            return Response(
                {
                    'loan_id': None,
                    'customer_id': data['customer_id'],
                    'loan_approved': False,
                    'message': result.message,
                    'monthly_installment': result.monthly_installment,
                },
                status=status.HTTP_200_OK,
            )
        from datetime import date
        from dateutil.relativedelta import relativedelta

        customer = Customer.objects.get(pk=data['customer_id'])
        monthly_repayment = result.monthly_installment
        start_date = date.today()
        end_date = start_date + relativedelta(months=data['tenure'])
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=data['loan_amount'],
            tenure=data['tenure'],
            interest_rate=result.corrected_interest_rate,
            monthly_repayment=monthly_repayment,
            emis_paid_on_time=0,
            emis_paid=0,
            start_date=start_date,
            end_date=end_date,
        )
        loan.loan_id = loan.pk
        loan.save(update_fields=['loan_id'])
        return Response(
            {
                'loan_id': loan.loan_id or loan.pk,
                'customer_id': customer.pk,
                'loan_approved': True,
                'message': 'Loan approved',
                'monthly_installment': result.monthly_installment,
            },
            status=status.HTTP_201_CREATED,
        )


class ViewLoanView(APIView):
    def get(self, request, loan_id):
        try:
            loan = Loan.objects.select_related('customer').filter(
                Q(pk=loan_id) | Q(loan_id=loan_id)
            ).first()
            if loan is None:
                raise Loan.DoesNotExist()
        except Loan.DoesNotExist:
            return Response(
                {'detail': 'Loan not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LoanDetailSerializer(loan)
        data = serializer.data
        data['loan_id'] = loan.loan_id if loan.loan_id is not None else loan.pk
        return Response(data, status=status.HTTP_200_OK)


class ViewLoansView(APIView):
    def get(self, request, customer_id):
        try:
            Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {'detail': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        loans = Loan.objects.filter(customer_id=customer_id).order_by('-id')
        serializer = LoanListItemSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
