from django.urls import path
from . import views

urlpatterns = [
    # Accounts
    path(
        'accounts/',
        views.AccountListCreateView.as_view(),
        name='account-list-create'
    ),
    path(
        'accounts/<uuid:pk>/',
        views.AccountDetailView.as_view(),
        name='account-detail'
    ),

    # Transactions
    path(
        'accounts/<uuid:account_id>/transactions/',
        views.TransactionCreateView.as_view(),
        name='transaction-create'
    ),
    path(
        'accounts/<uuid:account_id>/transactions/list/',
        views.TransactionListView.as_view(),
        name='transaction-list'
    ),

    # Transfers
    path(
        'transfers/',
        views.TransferCreateView.as_view(),
        name='transfer-create'
    ),
]
