import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

class Account(models.Model):
    """Model representing a financial account."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=3, default='USD')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                  validators=[MinValueValidator(Decimal('0.00'))])

    def __str__(self):
        return f"{self.owner_name} ({self.currency}) - {self.balance}"


class Transaction(models.Model):
    """Model representing a financial transaction."""

    class TransactionType(models.TextChoices):
        CREDIT = 'CREDIT', 'credit'
        DEBIT = 'DEBIT', 'debit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transactions')
    type = models.CharField(max_length=10, choices=TransactionType)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    external_idempotency_key = models.CharField(max_length=255, blank=True, null=True, unique=True)
    transfer = models.ForeignKey('Transfer', on_delete=models.PROTECT,null=True, blank=True,
                                 related_name='transactions')

    def save(self, *args, **kwargs):
        if self.pk and Transaction.objects.filter(pk=self.pk).exists():
            raise ValueError("Transactions are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Transactions are immutable and cannot be deleted.")

    def __str__(self):
        return f"{self.type} {self.amount} on {self.account.owner_name}"


class Transfer(models.Model):
    """Model representing a transfer between two accounts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='outgoing_transfers')
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='incoming_transfers')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    external_idempotency_key = models.CharField(max_length=255, blank=True, null=True, unique=True)

    def __str__(self):
        return f"Transfer {self.amount} from {self.from_account.owner_name} to {self.to_account.owner_name}"


class Event(models.Model):
    """Model representing an event in the ledger."""

    class EventType(models.TextChoices):
        TRANSACTION_CREATED = 'TRANSACTION_CREATED', 'Transaction Created'
        TRANSFER_CREATED = 'TRANSFER_CREATED', 'Transfer Created'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EventType)
    event_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} at {self.created_at}"
