''' 
This command fetches the Assets product (balance) only for each item in the fin_items 
tables (for wave => 3, deleted = 0, inactive = 0) and populates the fin_accounts_balances table
'''
from django.core.management.base import BaseCommand, CommandError
import base64
import os
import time
import plaid
import json
import logging
import sys

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.core import serializers

from datetime import datetime, timedelta

from fin.models import Fin_Items, Fin_Accounts_Balances, Fin_Accounts
from fin.functions import *
from users.models import User_Treatments, Treatments

client = plaid.Client(client_id=settings.PLAID_CLIENT_ID, secret=settings.PLAID_SECRET, public_key=settings.PLAID_PUBLIC_KEY, environment=settings.PLAID_ENV, api_version='2019-05-29')
days_of_historic_data = 730

def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True))


def fetch_assets(assets_token):
    num_retries_remaining = 20
    asset_report_json = None
    asset_report_error = None
    while num_retries_remaining > 0:
        try:
            asset_report_get_response = client.AssetReport.get(assets_token)
            asset_report_json = asset_report_get_response['report']
            # pretty_print_response(asset_report_get_response) # DEBUG
            # pretty_print_response(asset_report_json) # DEBUG
            break
        except plaid.errors.PlaidError as e:
            if e.code == 'PRODUCT_NOT_READY':
                num_retries_remaining -= 1
                time.sleep(2) # To prevent rate limit errors
                continue
            else:
                asset_report_error = {'error': {'error_code': e.code, 'error_type': e.type, 'display_message': e.display_message } }
                break

    # TODO - Handle error
    if num_retries_remaining == 0: # Rare case where assets weren't recovered after 20 tries (num_retries_remaining)
        asset_report_error = {'error': {'error_code': 'UNCAUGHT_ERROR', 'error_type': 'NON_PLAID_ERROR', 'display_message': 'Could not fetch assets after {num_retries_remaining} retries' } }

    time.sleep(3) # To prevent rate limit errors
    return asset_report_json, asset_report_error

#  Fetch asset_report token.
#  Input: Item's access_token (can be a list)
#  Returns: asset_token, error (type, code, and desc)
def fetch_assets_token(access_token):
    asset_token = None
    asset_token_error = None
    try:
        asset_report_create_response = client.AssetReport.create([access_token], days_of_historic_data)
        asset_token = asset_report_create_response['asset_report_token']
        # pretty_print_response(asset_report_create_response) # DEBUG
    except plaid.errors.PlaidError as e:
        asset_token_error = {'error': {'error_code': e.code, 'error_type': e.type, 'display_message': e.display_message } }

    time.sleep(2) # To prevent rate limit errors
    return asset_token, asset_token_error


# TODO - What if p_account_id changes??
def save_assets(item_save, assets):
    items = assets['items']
    for item in items:
        for account in item['accounts']:
            account_id = account['account_id']
            for hist_balance in account['historical_balances']:
                try:
                    Fin_Accounts_Balances.objects.create(
                        p_account_id = account_id,
                        item_id = item_save,
                        p_balance = hist_balance['current'],
                        p_balance_date = hist_balance['date'],
                    )
                    # print(f'{item_save.id} - {account_id} - {hist_balance["current"]} - {hist_balance["date"]}') # DEBUG
                except IntegrityError as e:
                    # Ignoring duplicate for unique key conflicts (item_id, p_account_id, p_balance_date)
                    # TODO - This will change to account_id (FK to fin_accounts)
                    pass

class Command(BaseCommand):

    help = 'Populates assets product (historical balances) for all linked institutions (> wave 2)'

    def handle(self, *args, **kwargs):

        # Fetching all user_id that are in wave 3 or greater
        user_ids = User_Treatments.objects.filter(wave__gte=3).values_list('user_id', flat=True)

        # Get all item_ids and access_tokens for intitutions linked for > wave 2, that are not deleted or inactive
        items = Fin_Items.objects.filter(user_id__in=list(user_ids)).filter(inactive=0).exclude(p_access_token=None,deleted=1).order_by('-id')

        # Loop through items
        for item in items:
            access_token = item.p_access_token
            assets_token = item.p_assets_token

            if assets_token: # Already have an assets_token
                print(f'+ ASSET_TOKEN_OLD: {item.id} - {access_token} - {assets_token}') # DEBUG
                # assets_token = 'assets-production-c2a26533-138d-40f0-8cbf-08846316b3c'
                assets, assets_error = fetch_assets(assets_token) # Fetch Assets
                if assets_error:
                    # If asset_report_token in fin_items is incorrect
                    if assets_error['error']['error_code'] == 'INVALID_ASSET_REPORT_TOKEN':
                        print(f'- ASSET_REPORT_FAIL: {item.id} - {assets_error}') # DEBUG
                        assets_token, assets_token_error = fetch_assets_token(access_token) # Fetch Assets Token
                        if assets_token_error:
                            print(f'- ASSET_TOKEN_FAIL: {item.id} - {access_token} - {assets_token_error}') # DEBUG
                        else:
                            item.p_assets_token = assets_token; item.save() # Update fin_items.p_assets_token
                            print(f'+ ASSET_TOKEN_RENEW: {item.id} - {access_token} - {assets_token}') # DEBUG
                            assets, assets_error = fetch_assets(assets_token) # Fetch Assets
                            if assets_error:
                                print(f'- ASSET_REPORT_FAIL: {item.id} - {assets_error}') # DEBUG
                            else:
                                save_assets(item, assets)
                    else:
                        print(f'Error getting assets balances for item id={item.id}: {assets_error}') # DEBUG
                else:
                   save_assets(item, assets)
            else: # No assets token in Fin_Items table
                assets_token, assets_token_error = fetch_assets_token(access_token) # Fetch Assets Token
                if assets_token_error:
                    # TODO: Some access_tokens are not working = this is because of me overriding the inactive = 0 for inactive = 1
                    print(f'- ASSET_TOKEN_FAIL: {item.id} - {access_token} - {assets_token_error}') # DEBUG
                else:
                    item.p_assets_token = assets_token; item.save() # Update fin_items.p_assets_token
                    print(f'+ ASSET_TOKEN_NEW: {item.id} - {access_token} - {assets_token}') # DEBUG
                    assets, assets_error = fetch_assets(assets_token) # Fetch Assets
                    if assets_error:
                        print(f'- ASSET_REPORT_FAIL: {item.id} - {assets_error}') # DEBUG
                    else:
                        save_assets(item, assets)
