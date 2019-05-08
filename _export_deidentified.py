# python3 manage.py shell < _export_cfsi.py
import csv
import sys
import os
from django.conf import settings
from django.contrib.auth.models import User
from fin.models import Fin_Transactions
from django.db import IntegrityError
from datetime import date

csv_file = 'uasfin_deidentified_' + str(date.today()) + '.csv'

trans_objs = Fin_Transactions.objects.filter(p_pending=0,removed=0,account_id__item_id__user_id__pk__gte=1005)

with open(csv_file, 'w') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow(["user_id_internal", "fin_institution_id_internal", "fin_institution_inactive", "fin_institution_deleted", "account_id_internal", "account_balances_available", "account_balances_current", "account_balances_iso_currency_code", "account_balances_limit", "account_balances_unofficial_currency_code", "account_subtype", "account_type", "transaction_id_internal", "transaction_amount", "transaction_category", "transaction_category_id", "transaction_p_date", "transaction_iso_currency_code", "transaction_meta_payment_method", "transaction_meta_payment_processor", "transaction_transaction_type", "transaction_unofficial_currency_code"])
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
			user1, 
			item1, item5, item6, 
			account1, account4, account5, account6, account7, account8, account11, account12,
			transaction0, transaction2, transaction3, transaction4, transaction5, transaction6, transaction18, transaction19, transaction24, transaction25
		])

csvFile.close()
