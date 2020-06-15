from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_account, name='add_account'),
    path('add_plus/', views.add_account_plus, name='add_account_plus'),
    path('link/', views.link_account, name='link_account'),
    path('link_iframe/', views.link_iframe, name='link_iframe'),
    path('link_iframe/<str:next_question>', views.link_iframe, name='link_iframe'),
    path('link/result/', views.link_account_result, name='link_account_result'),
    path('link/summary/', views.link_account_summary, name='link_account_summary'),
    path('link/thankyou/', views.link_account_thankyou, name='link_account_thankyou'),
    path('relink/<int:item_id>', views.relink_account, name='relink_account'),
    path('plaid_link_on_success/', views.plaid_link_onSuccess, name = 'plaid_link_onSuccess'),
    path('plaid_link_on_event/', views.plaid_link_onEvent, name='plaid_link_onEvent'),
    path('plaid_link_on_exit/', views.plaid_link_onExit, name='plaid_link_onExit'),
    path('details/<int:item_id>', views.account_details, name='account_details'),
    path('transactions/<int:item_id>/<int:account_id>', views.account_transactions, name='account_transactions'),
    path('help/', views.help, name='help'),
    path( settings.PLAID_WEBHOOK_URL, views.webhook, name='webhook'),
    
    path('unlink/<int:item_id>', views.unlink_account, name='unlink_account'),

    path('reset/', views.reset_account, name='reset_account'),
 	
 	path('plaid_relink_on_exit/', views.plaid_relink_onExit, name='plaid_relink_onExit'),   
]
