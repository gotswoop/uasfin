from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('details/<int:item_id>', views.account_details, name='account_details'),
    path('transactions/<int:item_id>/<int:account_id>', views.account_transactions, name='account_transactions'),
    path('help/', views.help, name='help'),
    path( settings.PLAID_WEBHOOK_URL, views.webhook, name='webhook'),
    path('get_access_token/', views.get_access_token),
    path('remove_item/<int:item_id>', views.remove_item),
]
