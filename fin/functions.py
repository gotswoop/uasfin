#import base64
#import os
import datetime
import plaid
import json
#import time

from django.shortcuts import render
from .models import Items, Item_accounts, Item_account_transactions, Plaid_Link_Logs, User_Actions, Users_With_Atleast_One_Linked_Institution, Plaid_Webhook_Logs
from django.conf import settings
from django.contrib import messages
import logging
from django.core import serializers

# ------------------------------------------------------------------
# DEBUG: PRETTY PRINT RESPONSE
# ------------------------------------------------------------------
def pretty_print_response(response):
	print(json.dumps(response, indent=2, sort_keys=True))

# ------------------------------------------------------------------
# Get Transactions for an item
# ------------------------------------------------------------------
def fetch_transactions_from_plaid(access_token):
  
	# Pull transactions for the last 1095 days (3 years)
	start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-730))
	end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())

	try:
		transactions_response = client.Transactions.get(access_token, start_date, end_date)
	except plaid.errors.PlaidError as e:
		return jsonify(format_error(e))
  
	for transaction in transactions_response['transactions']:
		account_id = transaction['account_id']
		item_account_obj = Item_accounts.objects.get(p_account_id = account_id)
		if item_account_obj:
			try:
				already_exists = Item_account_transactions.objects.get(p_transaction_id = transaction['transaction_id'], item_accounts_id = item_account_obj)
			except Item_account_transactions.DoesNotExist:
				already_exists = None

			if already_exists:
				# Skip to next transaction
				continue

			insert_transaction(item_account_obj, transaction)
			# logger.debug('TRANSACTIONS ADDED: ' + serializers.serialize('json', [new_transaction]))
			logger.debug('TRANSACTIONS ADDED: ' + new_transaction.p_transaction_id)

		else:
			logger.debug('ERROR: Cannot find the account that we are trying to add or update transactions into')

	return None

def log_imcoming_webhook(incoming, remote_ip):

	new_plaid_webhook_log = Plaid_Webhook_Logs.objects.create(
		remote_ip = request.META.get('REMOTE_ADDR'),
		p_webhook_type = incoming.get('webhook_type'),
		p_webhook_code = incoming.get('webhook_code'),
		p_item_id  = incoming.get('item_id'),
		p_error = incoming.get('error'),
		p_new_transactions = incoming.get('new_transactions'),
		p_removed_transactions = incoming.get('removed_transactions'),
		p_raw_payload = incoming
	)

	return None

def insert_transaction(item_account_obj, transaction):

	new_transaction = Item_account_transactions.objects.create(
		item_accounts_id = item_account_obj,
		p_account_id = transaction['account_id'],
		p_account_owner = transaction['account_owner'],
		p_amount = transaction['amount'],
		p_category = json.dumps(transaction['category']),
		p_category_id = transaction['category_id'],
		p_date = transaction['date'],
		p_iso_currency_code = transaction['iso_currency_code'],
		p_location_address = transaction['location']['address'],
		p_location_city = transaction['location']['city'],
		p_location_lat = transaction['location']['lat'],
		p_location_lon = transaction['location']['lon'],
		p_location_state = transaction['location']['state'],
		p_location_store_number = transaction['location']['store_number'],
		p_location_zip = transaction['location']['zip'],
		p_name = transaction['name'],
		p_payment_meta_by_order_of = transaction['payment_meta']['by_order_of'],
		p_payment_meta_payee = transaction['payment_meta']['payee'],
		p_payment_meta_payer = transaction['payment_meta']['payer'],
		p_payment_meta_payment_method = transaction['payment_meta']['payment_method'],
		p_payment_meta_payment_processor = transaction['payment_meta']['payment_processor'],
		p_payment_meta_ppd_id = transaction['payment_meta']['ppd_id'],
		p_payment_meta_reason = transaction['payment_meta']['reason'],
		p_payment_meta_reference_number = transaction['payment_meta']['reference_number'],
		p_pending = transaction['pending'],
		p_pending_transaction_id = transaction['pending_transaction_id'],
		p_transaction_id = transaction['transaction_id'],
		p_transaction_type = transaction['transaction_type'],
		p_unofficial_currency_code = transaction['unofficial_currency_code']
	)

	return None
# ------------------------------------------------------------------
# Remove item (TESTING ONLY)
# ------------------------------------------------------------------
def format_error(e):
	return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }
