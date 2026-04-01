import logging
from .models import Event

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Lightweight event-driven hook.

    Publishes domain events when transactions or transfers are created.
    Currently backed by database storage + logging.

    In production, this could be extended to publish to:
    - Celery tasks
    - RabbitMQ / Kafka
    - Webhooks

    The interface remains the same — only the implementation changes.
    """

    @staticmethod
    def publish_transaction_created(transaction):
        """Publish event when a transaction is created."""
        payload = {
            'transaction_id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'type': transaction.type,
            'amount': str(transaction.amount),
            'description': transaction.description,
            'created_at': transaction.created_at.isoformat(),
        }

        event = Event.objects.create(
            event_type=Event.EventType.TRANSACTION_CREATED,
            event_data=payload,
        )

        logger.info(
            f"Event published: {event.event_type} | "
            f"Transaction: {transaction.id} | "
            f"Account: {transaction.account_id} | "
            f"Type: {transaction.type} | "
            f"Amount: {transaction.amount}"
        )

        return event

    @staticmethod
    def publish_transfer_created(transfer, debit_txn, credit_txn):
        """Publish event when a transfer is created."""
        payload = {
            'transfer_id': str(transfer.id),
            'from_account_id': str(transfer.from_account_id),
            'to_account_id': str(transfer.to_account_id),
            'amount': str(transfer.amount),
            'description': transfer.description,
            'debit_transaction_id': str(debit_txn.id),
            'credit_transaction_id': str(credit_txn.id),
            'created_at': transfer.created_at.isoformat(),
        }

        event = Event.objects.create(
            event_type=Event.EventType.TRANSFER_CREATED,
            event_data=payload,
        )

        logger.info(
            f"Event published: {event.event_type} | "
            f"Transfer: {transfer.id} | "
            f"From: {transfer.from_account_id} → To: {transfer.to_account_id} | "
            f"Amount: {transfer.amount}"
        )

        return event
