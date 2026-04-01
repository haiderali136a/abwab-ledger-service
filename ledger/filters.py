import django_filters
from .models import Account


class AccountFilter(django_filters.FilterSet):
    owner_name = django_filters.CharFilter(lookup_expr='icontains')
    currency = django_filters.CharFilter(lookup_expr='iexact')
    min_balance = django_filters.NumberFilter(
        field_name='balance', lookup_expr='gte'
    )
    max_balance = django_filters.NumberFilter(
        field_name='balance', lookup_expr='lte'
    )

    class Meta:
        model = Account
        fields = ['owner_name', 'currency']
