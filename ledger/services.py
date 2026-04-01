from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import F

from .models import Account, Transaction, Transfer
from .events import EventPublisher


class TransactionService:
    """
    Handles creation of transactions with atomic balance updates,
    idempotency handling, and event publishing.
    """

    @staticmethod
    def create_transaction(
            account_id: str,
            type: str,
            amount: Decimal,
            description: str = '',
            external_idempotency_key: str = None,
    ) -> Transaction:
        """Create a transaction for an account.

        - Validates sufficient funds for debits
        - Handles idempotency
        - Updates balance atomically
        - Publishes event
        """

        # Handle idempotency
        if external_idempotency_key:
            existing = Transaction.objects.filter(
                external_idempotency_key=external_idempotency_key
            ).first()

            if existing:
                # Same key exists — check if payload matches
                if (
                        str(existing.account_id) == str(account_id)
                        and existing.type == type
                        and existing.amount == amount
                ):
                    # Same request — return existing (idempotent)
                    return existing
                else:
                    # Different payload — conflict TODO
                    raise Exception(
                        "Idempotency key already used with different parameters."
                    )

        with db_transaction.atomic():
            # Lock the account row to prevent race conditions
            account = (
                Account.objects
                .select_for_update()
                .get(id=account_id)
            )

            if type == Transaction.TransactionType.DEBIT:
                if account.balance < amount:
                    raise Exception( # TODO
                        f"Insufficient funds. Available: {account.balance}, "
                        f"Requested: {amount}"
                    )
                account.balance = F('balance') - amount
            else:
                account.balance = F('balance') + amount

            account.save(update_fields=['balance', 'updated_at'])

            # Create immutable transaction record
            txn = Transaction.objects.create(
                account=account,
                type=type,
                amount=amount,
                description=description,
                external_idempotency_key=external_idempotency_key,
            )

        # Refresh to get actual balance value (F() expression)
        account.refresh_from_db()

        # Publish event (outside atomic block)
        EventPublisher.publish_transaction_created(txn)

        return txn


class TransferService:
    """
    Handles transfers between accounts with atomic guarantees.
    A transfer creates two linked transaction records.
    """

    @staticmethod
    def create_transfer(
            from_account_id: str,
            to_account_id: str,
            amount: Decimal,
            description: str = '',
            external_idempotency_key: str = None,
    ) -> Transfer:
        """
        Transfer money between two accounts.

        - Validates same currency
        - Validates sufficient funds
        - Creates debit + credit as one atomic operation
        - Handles idempotency
        - Publishes event
        """

        if str(from_account_id) == str(to_account_id):
            raise Exception( # TODO
                "Cannot transfer to the same account."
            )

        # Handle idempotency
        if external_idempotency_key:
            existing = Transfer.objects.filter(
                external_idempotency_key=external_idempotency_key
            ).first()

            if existing:
                if (
                        str(existing.from_account_id) == str(from_account_id)
                        and str(existing.to_account_id) == str(to_account_id)
                        and existing.amount == amount
                ):
                    return existing
                else:
                    raise Exception( # TODO
                        "Idempotency key already used with different parameters."
                    )

        with db_transaction.atomic():
            # Lock BOTH accounts — always in consistent order to prevent deadlocks
            account_ids = sorted([str(from_account_id), str(to_account_id)])
            accounts = (
                Account.objects
                .select_for_update()
                .filter(id__in=account_ids)
                .order_by('id')
            )

            accounts_dict = {str(a.id): a for a in accounts}

            if str(from_account_id) not in accounts_dict:
                raise Account.DoesNotExist("Source account not found.")
            if str(to_account_id) not in accounts_dict:
                raise Account.DoesNotExist("Destination account not found.")

            from_account = accounts_dict[str(from_account_id)]
            to_account = accounts_dict[str(to_account_id)]

            # Validate same currency
            if from_account.currency != to_account.currency:
                raise Exception( # TODO
                    f"Cannot transfer between different currencies: "
                    f"{from_account.currency} → {to_account.currency}"
                )

            # Validate sufficient funds
            if from_account.balance < amount:
                raise Exception( # TODO
                    f"Insufficient funds. Available: {from_account.balance}, "
                    f"Requested: {amount}"
                )

            # Create transfer record
            transfer = Transfer.objects.create(
                from_account=from_account,
                to_account=to_account,
                amount=amount,
                description=description,
                external_idempotency_key=external_idempotency_key,
            )

            # Debit source
            from_account.balance = F('balance') - amount
            from_account.save(update_fields=['balance', 'updated_at'])

            # Credit destination
            to_account.balance = F('balance') + amount
            to_account.save(update_fields=['balance', 'updated_at'])

            # Create linked transaction records
            debit_txn = Transaction.objects.create(
                account=from_account,
                type=Transaction.TransactionType.DEBIT,
                amount=amount,
                description=f"Transfer out: {description}",
                transfer=transfer,
            )

            credit_txn = Transaction.objects.create(
                account=to_account,
                type=Transaction.TransactionType.CREDIT,
                amount=amount,
                description=f"Transfer in: {description}",
                transfer=transfer,
            )

        # Publish event (outside atomic block)
        EventPublisher.publish_transfer_created(transfer, debit_txn, credit_txn)

        return transfer
