# Generated manually for credit_app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=20)),
                ('monthly_salary', models.IntegerField()),
                ('approved_limit', models.IntegerField()),
                ('current_debt', models.IntegerField(default=0)),
                ('age', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'credit_app_customer',
            },
        ),
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loan_id', models.IntegerField(blank=True, null=True, unique=True)),
                ('loan_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('tenure', models.IntegerField()),
                ('interest_rate', models.DecimalField(decimal_places=2, max_digits=6)),
                ('monthly_repayment', models.DecimalField(decimal_places=2, max_digits=15)),
                ('emis_paid_on_time', models.IntegerField(default=0)),
                ('emis_paid', models.IntegerField(default=0)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to='credit_app.customer')),
            ],
            options={
                'db_table': 'credit_app_loan',
            },
        ),
    ]
