from rest_framework import serializers
from decimal import Decimal
from .models import Account, Transaction, Transfer


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'owner_name', 'currency', 'balance', 'created_at']
        read_only_fields = ['id', 'balance', 'created_at']

    def validate_currency(self, value):
        """Validate ISO 4217 currency code."""
        allowed_currencies = ['SAR', 'USD', 'EUR', 'GBP', 'AED'] # Extend as needed
        value = value.upper()
        if value not in allowed_currencies:
            raise serializers.ValidationError(
                f"Invalid currency. Allowed: {', '.join(allowed_currencies)}"
            )
        return value


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'account', 'type', 'amount', 'description',
            'external_idempotency_key', 'transfer', 'created_at'
        ]
        read_only_fields = ['id', 'account', 'transfer', 'created_at']


class CreateTransactionSerializer(serializers.Serializer):
    """Serializer for creating a transaction."""
    type = serializers.ChoiceField(
        choices=Transaction.TransactionType.choices
    )
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(
        required=False,
        default='',
        allow_blank=True
    )
    external_idempotency_key = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        max_length=255
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value


class TransferSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id', 'from_account', 'to_account', 'amount',
            'description', 'external_idempotency_key', 'transactions', 'created_at'
        ]
        read_only_fields = ['id', 'transactions', 'created_at']


class CreateTransferSerializer(serializers.Serializer):
    """Serializer for creating a transfer."""
    from_account_id = serializers.UUIDField()
    to_account_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(
        required=False,
        default='',
        allow_blank=True
    )
    external_idempotency_key = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        max_length=255
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate(self, attrs):
        if attrs['from_account_id'] == attrs['to_account_id']:
            raise serializers.ValidationError(
                "Source and destination accounts must be different."
            )
        return attrs
