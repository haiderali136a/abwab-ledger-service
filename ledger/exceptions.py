from rest_framework.exceptions import APIException
from rest_framework import status


class InsufficientFundsError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Insufficient funds for this operation.'
    default_code = 'insufficient_funds'


class DuplicateIdempotencyKeyError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Idempotency key already used with different parameters.'
    default_code = 'duplicate_idempotency_key'


class CurrencyMismatchError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Cannot transfer between accounts with different currencies.'
    default_code = 'currency_mismatch'


class SameAccountTransferError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Cannot transfer to the same account.'
    default_code = 'same_account_transfer'
