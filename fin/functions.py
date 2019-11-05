# import base64
# import os
# import time
import plaid
import json
import logging

from django.shortcuts import render
from django.core import serializers
from django.db import IntegrityError
from django.conf import settings
from django.contrib import messages

from datetime import datetime, timedelta

from fin.models import Fin_Items, Fin_Accounts, Fin_Accounts_History, Fin_Transactions, Plaid_Link_Logs, Plaid_Webhook_Logs, User_Actions, Users_With_Linked_Institutions
from users.models import User_Treatments

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Fetch Transactions for an item from PLAID
# ------------------------------------------------------------------
def fetch_transactions_from_plaid(client, item):
  
	# Pull 300 (default) transactions for the last 1460 days (4 years)
	start_date = '{:%Y-%m-%d}'.format(datetime.now() + timedelta(days=-1460))
	end_date = '{:%Y-%m-%d}'.format(datetime.now())
	count = remaining_transactions = 300
	offset = 0
	first_iteration = True
	
	while True:

		# DEBUG
		# print('Fetching / Remaining / Offset: ' + str(count) + '/' + str(remaining_transactions) + '/' + str(offset))
		
		try:
			transactions_response = client.Transactions.get(item.p_access_token, start_date, end_date, {'count':count, 'offset':offset})
		except plaid.errors.PlaidError as e:
			msg = '# ERROR: Plaid Error @ client.Transactions.get. Access token = ' + str(item.p_access_token) + '. Details' + format(e)
			error_handler(msg)
			break

		incoming_transactions = transactions_response.get('total_transactions', 0)
		# DEBUG
		# print('INCOMING ACTUAL: ' + str(incoming_transactions))
		remaining_transactions = remaining_transactions - count
		# Setting offset for pagination
		offset = offset + count
		
		# Processing Transactions
		for transaction in transactions_response.get('transactions'):
		
			account_id = transaction.get('account_id')

			try:
				fin_accounts_obj = Fin_Accounts.objects.get(p_account_id = account_id)
			except Fin_Accounts.DoesNotExist:
				fin_accounts_obj = None

			if fin_accounts_obj:
				new_transaction = insert_transaction(fin_accounts_obj, transaction)
			else:
				msg = '# ERROR: Cannot find the corresponding account that we are trying to add transactions into Account_id = ' + account_id
				error_handler(msg)
  
		if first_iteration:
  			
			remaining_transactions = incoming_transactions - count
			first_iteration = False

			# Updating account balances (Once and done)
			for account in transactions_response.get('accounts'):
				try:
					fin_account = Fin_Accounts.objects.get(p_account_id = account.get('account_id'), item_id = item)
				except Fin_Accounts.DoesNotExist:
					msg = '# ERROR: Cannot find the account_id to update. ' + account.get('account_id')
					error_handler(msg)

				fin_account.p_balances_available = account.get('balances').get('available')
				fin_account.p_balances_current = account.get('balances').get('current')
				fin_account.p_balances_limit = account.get('balances').get('limit')
				fin_account.account_refresh_date = datetime.now()
				fin_account.save(update_fields=['p_balances_available','p_balances_current','p_balances_limit','account_refresh_date'])

				accounts_history = Fin_Accounts_History.objects.create(
					item_id = item,
					p_account_id = account.get('account_id'),
					p_balances_available = account.get('balances').get('available'),
					p_balances_current = account.get('balances').get('current'),
					p_balances_iso_currency_code = account.get('balances').get('iso_currency_code'),
					p_balances_limit = account.get('balances').get('limit'),
					p_balances_unofficial_currency_code = account.get('balances').get('unofficial_currency_code'),
					p_mask = account.get('mask'),
					p_name = account.get('name'),
					p_official_name = account.get('official_name'),
					p_subtype = account.get('subtype'),
					p_type = account.get('type')
				)
		
		# Exiting when nothing left to fetch from plaid
		if remaining_transactions < 1:
			break

	return None

# ------------------------------------------------------------------
# Inserting webhook activity from Plaid into db
# ------------------------------------------------------------------
def log_incoming_webhook(incoming, remote_ip):

	if incoming.get('error') is None:
		_error = incoming.get('error')
	else:
		_error = json.dumps(incoming.get('error'))

	try:
		new_plaid_webhook_log = Plaid_Webhook_Logs.objects.create(
			remote_ip = remote_ip,
			p_webhook_type = incoming.get('webhook_type'),
			p_webhook_code = incoming.get('webhook_code'),
			p_item_id  = incoming.get('item_id'),
			p_error = _error,
			p_new_transactions = incoming.get('new_transactions'),
			p_removed_transactions = incoming.get('removed_transactions'),
			p_raw_payload = json.dumps(incoming)
		)
	except IntegrityError as e:
		msg = '# ERROR - Plaid_Webhook_Log insert: ' + e.args
		error_handler(msg)

	return None

# ------------------------------------------------------------------
# Logging user actions 
# ------------------------------------------------------------------
def log_user_actions(request, action, institution_id, institution_name, error_code = None, error_message = None, p_link_session_id = None):

	try:
		User_Actions.objects.create(
			user_id = request.user,
			user_ip = request.META['REMOTE_ADDR'],
			action = action,
			institution_id = institution_id,
			institution_name = institution_name,
			error_code = error_code,
			error_message = error_message,
			p_link_session_id = p_link_session_id
		)
	except IntegrityError as e:
		msg = '# ERROR - user_actions insert: ' + e.args
		error_handler(msg)

	return None

# ------------------------------------------------------------------
# Inserting transactions fetched from Plaid into db
# Assumes old transactions are never updated
# ------------------------------------------------------------------
def insert_transaction(fin_accounts_obj, transaction):

	try:
		transaction, created = Fin_Transactions.objects.get_or_create(p_transaction_id = transaction.get('transaction_id'), account_id = fin_accounts_obj, 
		defaults={
			'p_account_owner': transaction.get('account_owner'),
			'p_amount': transaction.get('amount'),
			'p_category': transaction.get('category'),
			'p_category_id': transaction.get('category_id'),
			'p_date': transaction.get('date'),
			'p_iso_currency_code': transaction.get('iso_currency_code'),
			'p_location_address': transaction.get('location').get('address'),
			'p_location_city': transaction.get('location').get('city'),
			'p_location_lat': transaction.get('location').get('lat'),
			'p_location_lon': transaction.get('location').get('lon'),
			'p_location_state': transaction.get('location').get('state'),
			'p_location_store_number': transaction.get('location').get('store_number'),
			'p_location_zip': transaction.get('location').get('zip'),
			'p_name': transaction.get('name'),
			'p_payment_meta_by_order_of': transaction.get('payment_meta').get('by_order_of'),
			'p_payment_meta_payee': transaction.get('payment_meta').get('payee'),
			'p_payment_meta_payer': transaction.get('payment_meta').get('payer'),
			'p_payment_meta_payment_method': transaction.get('payment_meta').get('payment_method'),
			'p_payment_meta_payment_processor': transaction.get('payment_meta').get('payment_processor'),
			'p_payment_meta_ppd_id': transaction.get('payment_meta').get('ppd_id'),
			'p_payment_meta_reason':  transaction.get('payment_meta').get('reason'),
			'p_payment_meta_reference_number': transaction.get('payment_meta').get('reference_number'),
			'p_pending': transaction.get('pending'),
			'p_pending_transaction_id': transaction.get('pending_transaction_id'),
			'p_transaction_type': transaction.get('transaction_type'),
			'p_unofficial_currency_code': transaction.get('unofficial_currency_code')
			},
		)
	except IntegrityError as e:
		msg = '# ERROR - Transaction insert: ' + e.args
		error_handler(msg)
		return None

	# DEBUG
	'''
	if created:
		print('# Inserted transaction ' + transaction.p_transaction_id)
	else:
		print('# Duplicate ' + transaction.p_transaction_id)
	'''
	return created


# ------------------------------------------------------------------
# Fetch user's treatment. Return None if not found
# ------------------------------------------------------------------
def fetch_treatment(user_id):

	try:
		user_treatment = User_Treatments.objects.get(user_id = user_id)
	except User_Treatments.DoesNotExist:
		msg = '# ERROR - No treatment found for user_id ' + str(user_id)
		error_handler(msg)
		return None

	return user_treatment.treatment


def error_handler(msg, error_type="error", fatal=0):
	if error_type == "debug":
		logger.debug(msg)
	else:
		logger.error(msg)

	# TODO: if fatal == 1?
	return None

# ------------------------------------------------------------------
# DEBUG
# ------------------------------------------------------------------
def format_error(e):
	return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }

def pretty_print_response(response):
	print(json.dumps(response, indent=2, sort_keys=True))

