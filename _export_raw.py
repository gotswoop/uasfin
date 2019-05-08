# python3 manage.py shell < _export.py
import csv
import sys
import os
from django.conf import settings
from django.contrib.auth.models import User
from fin.models import Fin_Transactions
from django.db import IntegrityError
from datetime import date

csv_file = 'uasfin_identifiable_' + str(date.today()) + '.csv'

trans_objs = Fin_Transactions.objects.filter(p_pending=0,removed=0,account_id__item_id__user_id__pk__gte=1005)

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["panel_id", "user_id_internal", "fin_institution_id_internal", "fin_item_id", "fin_institution_id", "fin_institution_name", "fin_institution_inactive", "fin_institution_deleted", "account_id_internal", "account_id", "account_name", "account_balances_available", "account_balances_current", "account_balances_iso_currency_code", "account_balances_limit", "account_balances_unofficial_currency_code", "account_mask", "account_official_name", "account_subtype", "account_type", "transaction_id_internal", "transaction_account_owner", "transaction_amount", "transaction_category", "transaction_category_id", "transaction_p_date", "transaction_iso_currency_code", "transaction_location_address", "transaction_location_city", "transaction_location_lat", "transaction_location_lon", "transaction_location_state", "transaction_location_store_number", "transaction_location_zip", "transaction_name", "transaction_payment_meta_by_order_of", "transaction_meta_payee", "transaction_meta_payer", "transaction_meta_payment_method", "transaction_meta_payment_processor", "transaction_payment_meta_ppd_id", "transaction_payment_meta_reason", "transaction_payment_meta_reference_number", "transaction_transaction_id", "transaction_transaction_type", "transaction_unofficial_currency_code"])
	for t in trans_objs:
		user0 = t.account_id.item_id.user_id.username
		user1 = t.account_id.item_id.user_id.pk

		item1 = t.account_id.item_id.pk
		item2 = t.account_id.item_id.p_item_id
		item3 = t.account_id.item_id.p_institution_id
		item4 = t.account_id.item_id.p_item_name
		item5 = t.account_id.item_id.inactive
		item6 = t.account_id.item_id.deleted

		account1 = t.account_id.pk
		account2 = t.account_id.p_account_id
		account3 = t.account_id.p_name
		account4 = t.account_id.p_balances_available
		account5 = t.account_id.p_balances_current
		account6 = t.account_id.p_balances_iso_currency_code
		account7 = t.account_id.p_balances_limit
		account8 = t.account_id.p_balances_unofficial_currency_code
		account9 = t.account_id.p_mask
		account10 = t.account_id.p_official_name
		account11 = t.account_id.p_subtype
		account12 = t.account_id.p_type

		transaction0 = t.pk
		transaction1 = t.p_account_owner
		transaction2 = t.p_amount
		transaction3 = t.p_category
		transaction4 = t.p_category_id
		transaction5 = t.p_date
		transaction6 = t.p_iso_currency_code
		transaction7 = t.p_location_address
		transaction8 = t.p_location_city
		transaction9 = t.p_location_lat
		transaction10 = t.p_location_lon
		transaction11 = t.p_location_state
		transaction12 = t.p_location_store_number
		transaction13 = t.p_location_zip
		transaction14 = t.p_name
		transaction15 = t.p_payment_meta_by_order_of
		transaction16 = t.p_payment_meta_payee
		transaction17 = t.p_payment_meta_payer
		transaction18 = t.p_payment_meta_payment_method
		transaction19 = t.p_payment_meta_payment_processor
		transaction20 = t.p_payment_meta_ppd_id
		transaction21 = t.p_payment_meta_reason
		transaction22 = t.p_payment_meta_reference_number
		transaction23 = t.p_transaction_id
		transaction24 = t.p_transaction_type
		transaction25 = t.p_unofficial_currency_code

		writer.writerow([
			user0, user1, 
			item1, item2, item3, item4, item5, item6, 
			account1, account2, account3, account4, account5, account6, account7, account8, account9, account10, account11, account12,
			transaction0, transaction1, transaction2, transaction3, transaction4, transaction5, transaction6, transaction7, transaction8, transaction9, 
			transaction10, transaction11, transaction12, transaction13, transaction14, transaction15, transaction16, transaction17, 
			transaction18, transaction19, transaction20, transaction21, transaction22, transaction23, transaction24, transaction25]
		)

csvFile.close()
