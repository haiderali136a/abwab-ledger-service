# Abwab Ledger Service

A backend service for managing customer accounts and money movements (credits, debits, transfers).

Built with Python, Django, and Django REST Framework.

---

## Quick Start

### Using Docker

```bash
git clone https://github.com/haiderali136a/abwab-ledger-service.git
cd abwab-ledger-service
docker-compose up --build
```

Service available at: http://localhost:8000/api/


### Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Running Tests

```bash
python manage.py test
```

## API Endpoints

Interactive API documentation available at `/api/docs/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/accounts/ | Create an account |
| GET | /api/accounts/ | List accounts |
| GET | /api/accounts/{id}/ | Get account details |
| POST | /api/accounts/{id}/transactions/ | Create a transaction |
| GET | /api/accounts/{id}/transactions/list/ | List account transactions |
| POST | /api/transfers/ | Create a transfer |

### Filters

- `GET /api/accounts/?owner_name=haider` — filter by owner name (case-insensitive)
- `GET /api/accounts/?currency=SAR` — filter by currency

### Sample Requests

**Create Account:**
POST /api/accounts/
```json
{
  "owner_name": "Haider Ali",
  "currency": "USD"
}
```

**Create Transaction:**
POST /api/accounts/1/transactions/
```json
{
  "type": "CREDIT",
  "amount": 100.00,
  "description": "Initial deposit",
  "external_idempotency_key": "salary-jan-2024"
}
```

**Create Transfer:**
POST /api/transfers/
```json
{
  "from_account": 1,
  "to_account": 2,
  "amount": 50.00,
  "description": "Payment for services",
  "external_idempotency_key": "payment-2024-01-15"
}
```

### Error Responses

| Status | Scenario |
|--------|----------|
| 400 | Invalid input, insufficient funds, currency mismatch, same account transfer |
| 404 | Account not found |
| 409 | Idempotency key reused with different payload |

---

## Design Decisions

### Transfer Modeling

Transfers are modeled as both a dedicated `Transfer` entity and two linked immutable `Transaction` records (one DEBIT, one CREDIT). Each account's transaction history is complete — querying an account's transactions shows all movements including transfers. The `Transfer` record links both sides for traceability. This follows the double-entry bookkeeping principle.

### Idempotency

Handled at the service layer before acquiring database locks:

- If `idempotency_key` is provided and a matching record exists with the same payload → return the original result (no duplicate created)
- If the same key exists with a different payload → return `409 Conflict`
- If no key is provided → a new record is always created

The `idempotency_key` field is `nullable` with a `unique` constraint at the database level. Payload comparison uses `account_id`, `type`, and `amount` for transactions, and `from_account_id`, `to_account_id`, and `amount` for transfers.

### Atomicity & Consistency

- **`select_for_update()`** locks account rows before reading balance, preventing concurrent requests from producing incorrect results
- **`F()` expressions** generate atomic SQL (`SET balance = balance - 100`), avoiding stale reads
- **`transaction.atomic()`** wraps all operations — if any part fails, everything rolls back
- **Sorted lock ordering** for transfers: accounts are always locked in sorted ID order to prevent deadlocks between concurrent transfers (A→B and B→A)

### Event-Driven Hook

Used an explicit `EventPublisher` class instead of Django signals. Events are stored in the database (`Event` model with JSON payload) and logged. Published outside the atomic block so a failed event does not roll back the financial operation. The publisher can be extended to Celery, Kafka, or webhooks by changing the implementation without modifying the service layer.

### Service Layer

Business logic lives in `services.py`, separate from views and models. Views handle HTTP, services handle business rules. This keeps logic reusable and independently testable.

---

## Database

SQLite is used for simplicity. `select_for_update()` is used for row-level locking, but SQLite silently ignores it (uses database-level locking instead). In production, PostgreSQL would be used for proper row-level locking under concurrent load.

---

## Assumptions

- Authentication and authorization are out of scope
- Pagination is not implemented
- Currency validation uses a predefined set of ISO 4217 codes
- Transaction immutability is enforced at the application level
- UUID primary keys used instead of auto-incrementing integers

---

## Tradeoffs

| Decision | Reason |
|----------|--------|
| SQLite over Postgres | Simpler setup for evaluation |
| No pagination | Out of scope, would use cursor-based in production |
| Sync event publishing | Simple, would use Celery in production |
| Idempotency check before lock | Efficient but has a narrow race window before lock acquisition |

---

## Project Structure
```
abwab-ledger-service/
├── config/              # Django settings and root URLs
├── ledger/
│   ├── models.py        # Account, Transaction, Transfer, Event
│   ├── services.py      # Business logic
│   ├── serializers.py   # Validation and formatting
│   ├── views.py         # API endpoints
│   ├── events.py        # EventPublisher
│   ├── exceptions.py    # Custom exceptions
│   ├── filters.py       # List filters
│   └── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```
