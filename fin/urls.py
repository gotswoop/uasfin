from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('details/<int:account_id>', views.account_details, name='account_details'),
    path('help/', views.help, name='help'),
    path( settings.PLAID_WEBHOOK_URL, views.webhook, name='webhook'),
    path('get_access_token/', views.get_access_token),
]
