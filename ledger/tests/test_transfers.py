from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ledger.models import Account, Transaction, Transfer, Event


class TransferTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account_a = Account.objects.create(
            owner_name='Alice',
            currency='SAR',
            balance=Decimal('1000.00')
        )
        self.account_b = Account.objects.create(
            owner_name='Bob',
            currency='SAR',
            balance=Decimal('500.00')
        )
        self.url = '/api/transfers/'

    def test_transfer_success(self):
        response = self.client.post(self.url, {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(self.account_b.id),
            'amount': '200.00',
            'description': 'Pay back lunch'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()
        self.assertEqual(self.account_a.balance, Decimal('800.00'))
        self.assertEqual(self.account_b.balance, Decimal('700.00'))

    def test_transfer_creates_two_transactions(self):
        """Transfer should create linked debit and credit transactions."""
        response = self.client.post(self.url, {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(self.account_b.id),
            'amount': '100.00',
        })

        transfer_id = response.data['id']
        transactions = Transaction.objects.filter(transfer_id=transfer_id)
        self.assertEqual(transactions.count(), 2)

        debit = transactions.get(type='DEBIT')
        credit = transactions.get(type='CREDIT')
        self.assertEqual(debit.account_id, self.account_a.id)
        self.assertEqual(credit.account_id, self.account_b.id)
        self.assertEqual(debit.amount, Decimal('100.00'))
        self.assertEqual(credit.amount, Decimal('100.00'))

    def test_transfer_insufficient_funds(self):
        response = self.client.post(self.url, {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(self.account_b.id),
            'amount': '2000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Neither account should change
        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()
        self.assertEqual(self.account_a.balance, Decimal('1000.00'))
        self.assertEqual(self.account_b.balance, Decimal('500.00'))

    def test_transfer_atomicity(self):
        """If transfer fails, neither account should be modified."""
        original_a = self.account_a.balance
        original_b = self.account_b.balance

        # Attempt transfer with insufficient funds
        self.client.post(self.url, {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(self.account_b.id),
            'amount': '5000.00',
        })

        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()
        self.assertEqual(self.account_a.balance, original_a)
        self.assertEqual(self.account_b.balance, original_b)
        self.assertEqual(Transfer.objects.count(), 0)

    def test_transfer_different_currencies_rejected(self):
        usd_account = Account.objects.create(
            owner_name='Charlie',
            currency='USD',
            balance=Decimal('1000.00')
        )
        response = self.client.post(self.url, {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(usd_account.id),
            'amount': '100.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_same_account_rejected(self):
        response = self.client.post(self.url, {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(self.account_a.id),
            'amount': '100.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_idempotency(self):
        payload = {
            'from_account_id': str(self.account_a.id),
            'to_account_id': str(self.account_b.id),
            'amount': '100.00',
            'external_idempotency_key': 'transfer-001'
        }

        response1 = self.client.post(self.url, payload)
        response2 = self.client.post(self.url, payload)

        self.assertEqual(response1.data['id'], response2.data['id'])
        self.assertEqual(Transfer.objects.count(), 1)

        self.account_a.refresh_from_db()
        self.assertEqual(self.account_a.balance, Decimal('900.00'))


class TransferEventTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(
            owner_name='Test User',
            currency='SAR',
            balance=Decimal('1000.00')
        )

    def test_transfer_creates_event(self):
        account_b = Account.objects.create(
            owner_name='User B', currency='SAR'
        )
        self.client.post('/api/transfers/', {
            'from_account_id': str(self.account.id),
            'to_account_id': str(account_b.id),
            'amount': '50.00'
        })

        events = Event.objects.filter(
            event_type=Event.EventType.TRANSFER_CREATED
        )
        self.assertEqual(events.count(), 1)
