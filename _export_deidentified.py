# python3 manage.py shell < _export_deidentified.py
import csv
import sys
import os
from django.conf import settings
from django.contrib.auth.models import User
from fin.models import Fin_Items, Fin_Accounts, Fin_Accounts_History, Fin_Transactions, User_Actions, Plaid_Webhook_Logs
from django.db import IntegrityError
from datetime import date

csv_file = 'uasfin_deidentified_accounts.csv'
account_objs = Fin_Accounts.objects.filter(item_id__user_id__pk__gt=1005)

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["user_id_internal", "fin_institution_id_internal", "fin_institution_inactive", "fin_institution_deleted", "account_id_internal", "account_id_plaid", "account_balances_available", "account_balances_current", "account_balances_iso_currency_code", "account_balances_limit", "account_balances_unofficial_currency_code", "account_subtype", "account_type", "date_created", "date_updated"])
	for t in account_objs:
		# user0 = t.item_id.user_id.username
		user1 = t.item_id.user_id.pk

		item1 = t.item_id.pk
		# item2 = t.item_id.p_item_id
		# item3 = t.item_id.p_institution_id
		# item4 = t.item_id.p_item_name
		item5 = t.item_id.inactive
		item6 = t.item_id.deleted

		account1 = t.pk
		account2 = t.p_account_id
		# account3 = t.p_name
		account4 = t.p_balances_available
		account5 = t.p_balances_current
		account6 = t.p_balances_iso_currency_code
		account7 = t.p_balances_limit
		account8 = t.p_balances_unofficial_currency_code
		# account9 = t.p_mask
		# account10 = t.p_official_name
		account11 = t.p_subtype
		account12 = t.p_type
		account13 = t.date_created
		account14 = t.date_updated

		writer.writerow([
			user1,
			item1, item5, item6,
			account1, account2, account4, account5, account6, account7, account8, account11, account12, account13, account14
		])

csvFile.close()

csv_file = 'uasfin_deidentified_transactions.csv'
trans_objs = Fin_Transactions.objects.filter(p_pending=0,removed=0,account_id__item_id__user_id__pk__gt=1005)

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["account_id_internal", "transaction_id_internal", "transaction_amount", "transaction_category", "transaction_category_id", "transaction_p_date", "transaction_iso_currency_code", "transaction_meta_payment_method", "transaction_meta_payment_processor", "transaction_transaction_type", "transaction_unofficial_currency_code"])
	for t in trans_objs:
		# user0 = t.account_id.item_id.user_id.username
		user1 = t.account_id.item_id.user_id.pk

		item1 = t.account_id.item_id.pk
		# item2 = t.account_id.item_id.p_item_id
		# item3 = t.account_id.item_id.p_institution_id
		# item4 = t.account_id.item_id.p_item_name
		item5 = t.account_id.item_id.inactive
		item6 = t.account_id.item_id.deleted

		account1 = t.account_id.pk
		# account2 = t.account_id.p_account_id
		# account3 = t.account_id.p_name
		account4 = t.account_id.p_balances_available
		account5 = t.account_id.p_balances_current
		account6 = t.account_id.p_balances_iso_currency_code
		account7 = t.account_id.p_balances_limit
		account8 = t.account_id.p_balances_unofficial_currency_code
		# account9 = t.account_id.p_mask
		# account10 = t.account_id.p_official_name
		account11 = t.account_id.p_subtype
		account12 = t.account_id.p_type

		transaction0 = t.pk
		# transaction1 = t.p_account_owner
		transaction2 = t.p_amount
		transaction3 = t.p_category
		transaction4 = t.p_category_id
		transaction5 = t.p_date
		transaction6 = t.p_iso_currency_code
		# transaction7 = t.p_location_address
		# transaction8 = t.p_location_city
		# transaction9 = t.p_location_lat
		# transaction10 = t.p_location_lon
		# transaction11 = t.p_location_state
		# transaction12 = t.p_location_store_number
		# transaction13 = t.p_location_zip
		# transaction14 = t.p_name
		# transaction15 = t.p_payment_meta_by_order_of
		# transaction16 = t.p_payment_meta_payee
		# transaction17 = t.p_payment_meta_payer
		transaction18 = t.p_payment_meta_payment_method
		transaction19 = t.p_payment_meta_payment_processor
		# transaction20 = t.p_payment_meta_ppd_id
		# transaction21 = t.p_payment_meta_reason
		# transaction22 = t.p_payment_meta_reference_number
		# transaction23 = t.p_transaction_id
		transaction24 = t.p_transaction_type
		transaction25 = t.p_unofficial_currency_code

		writer.writerow([
			account1,
			transaction0, transaction2, transaction3, transaction4, transaction5, transaction6, transaction18, transaction19, transaction24, transaction25
		])

csvFile.close()

csv_file = 'uasfin_deidentified_accounts_history.csv'
account_objs = Fin_Accounts_History.objects.filter(item_id__user_id__pk__gt=1005)

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["user_id_internal", "fin_institution_id_internal", "fin_institution_inactive", "fin_institution_deleted", "account_id_plaid", "account_balances_available", "account_balances_current", "account_balances_iso_currency_code", "account_balances_limit", "account_balances_unofficial_currency_code", "account_subtype", "account_type", "date_created"])
	for t in account_objs:
		# user0 = t.item_id.user_id.username
		user1 = t.item_id.user_id.pk

		item1 = t.item_id.pk
		# item2 = t.item_id.p_item_id
		# item3 = t.item_id.p_institution_id
		# item4 = t.item_id.p_item_name
		item5 = t.item_id.inactive
		item6 = t.item_id.deleted

		# account1 = t.pk
		account2 = t.p_account_id
		# account3 = t.p_name
		account4 = t.p_balances_available
		account5 = t.p_balances_current
		account6 = t.p_balances_iso_currency_code
		account7 = t.p_balances_limit
		account8 = t.p_balances_unofficial_currency_code
		# account9 = t.p_mask
		# account10 = t.p_official_name
		account11 = t.p_subtype
		account12 = t.p_type
		account13 = t.date_created

		writer.writerow([
			user1,
			item1, item5, item6,
			account2, account4, account5, account6, account7, account8, account11, account12, account13
		])

csvFile.close()

csv_file = 'uasfin_deidentified_user_actions.csv'
# select user_id, action, institution_id, error_code, error_message, date_created from user_actions order by date_created
account_objs = User_Actions.objects.filter(user_id__pk__gt=1005).order_by('date_created')

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["time_stamp", "user_id_internal", "action", "fin_institution_id_internal", "error_code", "error_message"])
	for t in account_objs:

		user = t.user_id.pk
		action = t.action
		if t.institution_id:
			try:
				inst_id = Fin_Items.objects.get(user_id=user, p_institution_id=t.institution_id).id
			except Fin_Items.DoesNotExist:
				# This is the case where there is no entry for for the instiution id in the Fin_Items table
				# Occurs only for an unsuccessful linking where I try to add an institution but never completed or was unsuccessful
				inst_id = -1
		else:
			inst_id = None
		error_code = t.error_code
		error_message = t.error_message
		date_created = t.date_created

		writer.writerow([date_created, user, action, inst_id, error_code, error_message])

csvFile.close()

csv_file = 'uasfin_deidentified_account_inactive_webhooks.csv'
# select date_created, p_item_id, p_error from plaid_webhook_logs where p_webhook_type = 'ITEM' ORDER BY date_created;
account_objs = Plaid_Webhook_Logs.objects.exclude(p_item_id=None).filter(p_webhook_type="ITEM").order_by('date_created')

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["time_stamp", "user_id_internal", "fin_institution_id_internal", "webook_error_from_plaid"])
	for t in account_objs:

		try:
			fin_item = Fin_Items.objects.get(p_item_id=t.p_item_id,user_id__pk__gt=1005)
		except Fin_Items.DoesNotExist:
			fin_item = None
			# Should never occur, but just in case

		if fin_item:
			user = fin_item.user_id.pk
			inst_id = fin_item.id
			error = t.p_error
			date_created = t.date_created
			writer.writerow([date_created, user, inst_id, error])

csvFile.close()
