from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Account, Transaction
from .serializers import (
    AccountSerializer,
    TransactionSerializer,
    CreateTransactionSerializer,
    TransferSerializer,
    CreateTransferSerializer,
)
from .services import TransactionService, TransferService
from .filters import AccountFilter


class AccountListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/accounts/     — List accounts (with filtering)
    POST /api/accounts/     — Create an account
    """
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AccountFilter


class AccountDetailView(generics.RetrieveAPIView):
    """
    GET /api/accounts/<id>/ — Get account details
    """
    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class TransactionCreateView(APIView):
    """
    POST /api/accounts/<account_id>/transactions/ — Create a transaction
    """

    def post(self, request, account_id):
        serializer = CreateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify account exists
        try:
            Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"error": "Account not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        transaction = TransactionService.create_transaction(
            account_id=account_id,
            type=serializer.validated_data['type'],
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data.get('description', ''),
            external_idempotency_key=serializer.validated_data.get('external_idempotency_key'),
        )

        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED
        )


class TransactionListView(generics.ListAPIView):
    """
    GET /api/accounts/<account_id>/transactions/ — List transactions for an account
    """
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(
            account_id=self.kwargs['account_id']
        ).select_related('account', 'transfer')


class TransferCreateView(APIView):
    """
    POST /api/transfers/ — Create a transfer between two accounts
    """

    def post(self, request):
        serializer = CreateTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer = TransferService.create_transfer(
            from_account_id=serializer.validated_data['from_account_id'],
            to_account_id=serializer.validated_data['to_account_id'],
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data.get('description', ''),
            external_idempotency_key=serializer.validated_data.get('external_idempotency_key'),
        )

        return Response(
            TransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED
        )
