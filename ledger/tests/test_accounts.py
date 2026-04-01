from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ledger.models import Account


class AccountCreationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_account_success(self):
        response = self.client.post('/api/accounts/', {
            'owner_name': 'Haider Ali',
            'currency': 'SAR'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner_name'], 'Haider Ali')
        self.assertEqual(response.data['currency'], 'SAR')
        self.assertEqual(Decimal(response.data['balance']), Decimal('0.00'))

    def test_create_account_missing_fields(self):
        response = self.client.post('/api/accounts/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_account_invalid_currency(self):
        response = self.client.post('/api/accounts/', {
            'owner_name': 'Test User',
            'currency': 'XYZ'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AccountRetrievalTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(
            owner_name='Test User',
            currency='SAR',
            balance=Decimal('1000.00')
        )

    def test_get_account_detail(self):
        response = self.client.get(f'/api/accounts/{self.account.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['balance']), Decimal('1000.00'))

    def test_get_nonexistent_account(self):
        import uuid
        fake_id = uuid.uuid4()
        response = self.client.get(f'/api/accounts/{fake_id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_accounts(self):
        Account.objects.create(owner_name='User 2', currency='USD')
        response = self.client.get('/api/accounts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_accounts_by_owner_name(self):
        Account.objects.create(owner_name='Another User', currency='USD')
        response = self.client.get('/api/accounts/?owner_name=Test')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['owner_name'], 'Test User')
