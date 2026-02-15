# Credit Approval System

Django 4 + DRF backend with PostgreSQL and Celery. No frontend.

## Quick start

1. Place `customer_data.xlsx` and `loan_data.xlsx` in the `data/` directory (columns: customer_id, first_name, last_name, phone_number, monthly_salary, approved_limit, current_debt; and customer_id, loan_id, loan amount, tenure, interest rate, monthly repayment, EMIs paid on time, start date, end date).

2. Copy `.env.example` to `.env` and set `SECRET_KEY` (and optionally DB/Redis).

3. Run everything with Docker:

   ```bash
   docker compose up --build
   ```

   API: http://localhost:8000

4. Ingest initial data (run after app and Celery are up):

   ```bash
   docker compose run app python manage.py ingest_initial_data
   ```

   Or run ingestion synchronously (no Celery):

   ```bash
   docker compose run app python manage.py ingest_initial_data --sync
   ```

   If you already ingested data before and new `/register` calls fail with 500, reset the customer ID sequence once:

   ```bash
   docker compose run --rm app python manage.py reset_customer_sequence
   ```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register customer (body: first_name, last_name, age, monthly_income, phone_number) |
| POST | `/check-eligibility` | Check loan eligibility (body: customer_id, loan_amount, interest_rate, tenure) |
| POST | `/create-loan` | Create loan if eligible (body: customer_id, loan_amount, interest_rate, tenure) |
| GET | `/view-loan/<loan_id>` | Loan details and customer |
| GET | `/view-loans/<customer_id>` | All loans for customer |

## Tests

Run unit and API tests:

```bash
docker compose run --rm app python manage.py test credit_app
```

## Stack

- Django 4, Django REST Framework
- PostgreSQL 15, Redis
- Celery (background ingestion)
- Gunicorn
