from django.db import models


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    monthly_salary = models.IntegerField()
    approved_limit = models.IntegerField()
    current_debt = models.IntegerField(default=0)
    age = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'credit_app_customer'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_id = models.IntegerField(unique=True, null=True, blank=True)
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    tenure = models.IntegerField()
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)
    monthly_repayment = models.DecimalField(max_digits=15, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    emis_paid = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'credit_app_loan'

    @property
    def repayments_left(self):
        return max(0, self.tenure - self.emis_paid)
