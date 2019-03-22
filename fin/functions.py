#import base64
#import os
from datetime import datetime, timedelta
import plaid
import json
#import time

from django.shortcuts import render
from .models import Fin_Items, Fin_Accounts, Fin_Transactions, Plaid_Link_Logs, Plaid_Webhook_Logs, User_Actions, Users_With_Linked_Institutions
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
def fetch_transactions_from_plaid(client, item, logger):
  
	# Pull transactions for the last 1460 days (4 years)
	start_date = '{:%Y-%m-%d}'.format(datetime.now() + timedelta(days=-1460))
	end_date = '{:%Y-%m-%d}'.format(datetime.now())
	count = 300
	offset = 0
	
	try:
		transactions_response = client.Transactions.get(item.p_access_token, start_date, end_date, {'count':count, 'offset':offset})
	except plaid.errors.PlaidError as e:
		return format_error(e)
  

	# pretty_print_response(transactions_response)
	# Update account information here. (just once)
	for account in transactions_response['accounts']:
		try:
			fin_account = Fin_Accounts.objects.get(p_account_id = account.get('account_id'), items_id = item)
		except Fin_Accounts.DoesNotExist:
			print ("IN MEAW")

		fin_account.p_balances_available = account.get('balances').get('available')
		fin_account.p_balances_current = account.get('balances').get('current')
		fin_account.p_balances_limit = account.get('balances').get('limit')
		fin_account.account_refresh_date = datetime.now()
		fin_account.save(update_fields=['p_balances_available','p_balances_current','p_balances_limit','account_refresh_date'])


	for transaction in transactions_response['transactions']:
		
		account_id = transaction['account_id']
		try:
			fin_accounts_obj = Fin_Accounts.objects.get(p_account_id = account_id)
		except Fin_Accounts.DoesNotExist:
			fin_accounts_obj = None

		if fin_accounts_obj:
			try:
				# TOO EXPENSIVE
				already_exists = Fin_Transactions.objects.get(p_transaction_id = transaction['transaction_id'], item_accounts_id = fin_accounts_obj)
			except Fin_Transactions.DoesNotExist:
				already_exists = None

			if already_exists:
				continue

			# TODO: What about updates?
			new_transaction = insert_transaction(fin_accounts_obj, transaction)
			# logger.debug('TRANSACTIONS ADDED: ' + serializers.serialize('json', [new_transaction]))
			logger.debug('TRANSACTIONS ADDED: ' + new_transaction.p_transaction_id)

		else:
			logger.debug('ERROR: Cannot find the account that we are trying to add or update transactions into')


	remaining_transactions = transactions_response['total_transactions'] - count

	while remaining_transactions > 0:
		offset = offset + count - 1
		print("REMAINING / count / offset : " + str(remaining_transactions) + '/' + str(count) + '/' + str(offset))

		try:
			transactions_response = client.Transactions.get(item.p_access_token, start_date, end_date, {'count':count, 'offset':offset})
		except plaid.errors.PlaidError as e:
			return format_error(e)
  		
		for transaction in transactions_response['transactions']:
		
			account_id = transaction['account_id']
			try:
				fin_accounts_obj = Fin_Accounts.objects.get(p_account_id = account_id)
			except Fin_Accounts.DoesNotExist:
				fin_accounts_obj = None

			if fin_accounts_obj:
				try:
					# TOO EXPENSIVE
					already_exists = Fin_Transactions.objects.get(p_transaction_id = transaction['transaction_id'], item_accounts_id = fin_accounts_obj)
				except Fin_Transactions.DoesNotExist:
					already_exists = None

				if already_exists:
					continue

				# TODO: What about updates?
				new_transaction = insert_transaction(fin_accounts_obj, transaction)
				# logger.debug('TRANSACTIONS ADDED: ' + serializers.serialize('json', [new_transaction]))
				logger.debug('TRANSACTIONS ADDED: ' + new_transaction.p_transaction_id)

			else:
				logger.debug('ERROR: Cannot find the account that we are trying to add or update transactions into')

		remaining_transactions = remaining_transactions - count
		
	return None

def log_incoming_webhook(incoming, remote_ip):

	# TODO: error handling
	new_plaid_webhook_log = Plaid_Webhook_Logs.objects.create(
		remote_ip = remote_ip,
		p_webhook_type = incoming.get('webhook_type'),
		p_webhook_code = incoming.get('webhook_code'),
		p_item_id  = incoming.get('item_id'),
		p_error = incoming.get('error'),
		p_new_transactions = incoming.get('new_transactions'),
		p_removed_transactions = incoming.get('removed_transactions'),
		p_raw_payload = incoming
	)

	return None

def insert_transaction(fin_accounts_obj, transaction):

	new_transaction = Fin_Transactions.objects.create(
		item_accounts_id = fin_accounts_obj,
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

	return new_transaction
# ------------------------------------------------------------------
# Remove item (TESTING ONLY)
# ------------------------------------------------------------------
def format_error(e):
	return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }
