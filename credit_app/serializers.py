from rest_framework import serializers

from .models import Customer, Loan


def approved_limit_from_salary(monthly_salary: int) -> int:
    """Approved limit = 36 * monthly_salary rounded to nearest lakh (1 lakh = 100000)."""
    return round(36 * monthly_salary / 100000) * 100000


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=1, max_value=120)
    monthly_income = serializers.IntegerField(min_value=0)
    phone_number = serializers.IntegerField()

    def create(self, validated_data):
        monthly_salary = validated_data['monthly_income']
        approved_limit = approved_limit_from_salary(monthly_salary)
        return Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            age=validated_data['age'],
            phone_number=str(validated_data['phone_number']),
            monthly_salary=monthly_salary,
            approved_limit=approved_limit,
            current_debt=0,
        )


class CheckEligibilitySerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=6, decimal_places=2)
    tenure = serializers.IntegerField(min_value=1)


class CreateLoanSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=6, decimal_places=2)
    tenure = serializers.IntegerField(min_value=1)


class CustomerNestedSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'age']


class LoanDetailSerializer(serializers.ModelSerializer):
    loan_id = serializers.SerializerMethodField()
    customer = CustomerNestedSerializer(read_only=True)
    monthly_installment = serializers.DecimalField(
        source='monthly_repayment', max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer', 'loan_amount', 'interest_rate',
            'monthly_installment', 'tenure',
        ]

    def get_loan_id(self, obj):
        return obj.loan_id if obj.loan_id is not None else obj.pk


class LoanListItemSerializer(serializers.ModelSerializer):
    loan_id = serializers.SerializerMethodField()
    monthly_installment = serializers.DecimalField(
        source='monthly_repayment', max_digits=15, decimal_places=2, read_only=True
    )
    repayments_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'loan_amount', 'interest_rate',
            'monthly_installment', 'repayments_left',
        ]

    def get_loan_id(self, obj):
        return obj.loan_id if obj.loan_id is not None else obj.pk
