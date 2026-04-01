from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ledger.models import Account, Transaction, Event


class CreditTransactionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(
            owner_name='Test User',
            currency='SAR'
        )
        self.url = f'/api/accounts/{self.account.id}/transactions/'

    def test_credit_success(self):
        response = self.client.post(self.url, {
            'type': 'CREDIT',
            'amount': '100.50',
            'description': 'Salary'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.50'))

    def test_multiple_credits(self):
        self.client.post(self.url, {
            'type': 'CREDIT', 'amount': '100.00', 'description': 'First'
        })
        self.client.post(self.url, {
            'type': 'CREDIT', 'amount': '50.00', 'description': 'Second'
        })
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('150.00'))


class DebitTransactionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(
            owner_name='Test User',
            currency='SAR',
            balance=Decimal('500.00')
        )
        self.url = f'/api/accounts/{self.account.id}/transactions/'

    def test_debit_success(self):
        response = self.client.post(self.url, {
            'type': 'DEBIT',
            'amount': '200.00',
            'description': 'Rent'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('300.00'))

    def test_debit_insufficient_funds(self):
        response = self.client.post(self.url, {
            'type': 'DEBIT',
            'amount': '600.00',
            'description': 'Too much'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('insufficient', response.data['detail'].lower())
        # Balance should be unchanged
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('500.00'))

    def test_debit_exact_balance(self):
        """Should allow debiting the exact balance (balance goes to 0)."""
        response = self.client.post(self.url, {
            'type': 'DEBIT',
            'amount': '500.00',
            'description': 'Withdraw all'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('0.00'))

    def test_negative_amount_rejected(self):
        response = self.client.post(self.url, {
            'type': 'CREDIT',
            'amount': '-50.00',
            'description': 'Negative'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_rejected(self):
        response = self.client.post(self.url, {
            'type': 'CREDIT',
            'amount': '0.00',
            'description': 'Zero'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_account(self):
        import uuid
        url = f'/api/accounts/{uuid.uuid4()}/transactions/'
        response = self.client.post(url, {
            'type': 'CREDIT',
            'amount': '100.00'
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transaction_immutability(self):
        """Transactions should not be modifiable."""
        txn = Transaction.objects.create(
            account=self.account,
            type='CREDIT',
            amount=Decimal('100.00'),
            description='Test'
        )
        with self.assertRaises(ValueError):
            txn.description = 'Modified'
            txn.save()


class IdempotencyTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(
            owner_name='Test User',
            currency='SAR',
            balance=Decimal('1000.00')
        )
        self.url = f'/api/accounts/{self.account.id}/transactions/'

    def test_idempotent_credit_same_key_same_event_data(self):
        """Same idempotency key + same event_data = return original, no duplicate."""
        payload = {
            'type': 'CREDIT',
            'amount': '100.00',
            'description': 'Salary',
            'external_idempotency_key': 'salary-jan-2024'
        }

        response1 = self.client.post(self.url, payload)
        response2 = self.client.post(self.url, payload)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Same transaction returned
        self.assertEqual(response1.data['id'], response2.data['id'])

        # Only ONE transaction created
        self.assertEqual(Transaction.objects.count(), 1)

        # Balance only updated ONCE
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1100.00'))

    def test_idempotent_key_different_event_data_returns_409(self):
        """Same idempotency key + different event_data = 409 Conflict."""
        self.client.post(self.url, {
            'type': 'CREDIT',
            'amount': '100.00',
            'external_idempotency_key': 'key-123'
        })

        response = self.client.post(self.url, {
            'type': 'CREDIT',
            'amount': '200.00',  # Different amount
            'external_idempotency_key': 'key-123'  # Same key
        })

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_no_idempotency_key_creates_multiple(self):
        """Without idempotency key, duplicate event_data create separate transactions."""
        payload = {
            'type': 'CREDIT',
            'amount': '100.00',
            'description': 'Deposit'
        }

        self.client.post(self.url, payload)
        self.client.post(self.url, payload)

        self.assertEqual(Transaction.objects.count(), 2)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1200.00'))

    def test_null_idempotency_key_allows_duplicates(self):
        """Null idempotency keys should not conflict with each other."""
        payload = {
            'type': 'CREDIT',
            'amount': '50.00',
            'external_idempotency_key': None
        }

        response1 = self.client.post(self.url, payload)
        response2 = self.client.post(self.url, payload)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response1.data['id'], response2.data['id'])


class TransactionEventTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(
            owner_name='Test User',
            currency='SAR',
            balance=Decimal('1000.00')
        )

    def test_transaction_creates_event(self):
        self.client.post(
            f'/api/accounts/{self.account.id}/transactions/',
            {'type': 'CREDIT', 'amount': '100.00'}
        )

        events = Event.objects.filter(
            event_type=Event.EventType.TRANSACTION_CREATED
        )
        self.assertEqual(events.count(), 1)
        self.assertEqual(
            events.first().event_data['account_id'],
            str(self.account.id)
        )
