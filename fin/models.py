import json
from django.db import models
from django.contrib.auth.models import User
from django_mysql.models import JSONField

def my_default():
    return {'foo': 'bar'}

class Fin_Items(models.Model):
	user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.PROTECT)
	p_institution_id = models.CharField(max_length=250)
	p_item_name = models.CharField(max_length=250)
	p_item_id = models.CharField(max_length=250)
	p_access_token = models.CharField(max_length=250, null=True)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)
	item_refresh_date = models.DateTimeField(null=True)
	inactive = models.IntegerField(default=0)
	inactive_date = models.DateTimeField(null=True)
	inactive_status = models.CharField(max_length=100, null=True)
	deleted = models.IntegerField(default=0)
	deleted_date = models.DateTimeField(null=True)
	
	class Meta:
		unique_together = ("user_id", "p_institution_id")
		db_table = "fin_items"

class Fin_Accounts(models.Model):
	items_id = models.ForeignKey(Fin_Items, db_column='items_id', on_delete=models.PROTECT)
	p_account_id = models.CharField(max_length=250)
	p_balances_available = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_balances_current = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_balances_iso_currency_code = models.CharField(max_length=10, default="USD", null=True)
	p_balances_limit = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_balances_unofficial_currency_code = models.CharField(max_length=50, null=True)
	p_mask = models.CharField(max_length=50, null=True)
	p_name = models.CharField(max_length=250, null=True)
	p_official_name = models.CharField(max_length=250, null=True)
	p_subtype = models.CharField(max_length=100, null=True)
	p_type = models.CharField(max_length=100, null=True)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)
	account_refresh_date = models.DateTimeField(null=True)
	
	class Meta:
		unique_together = ("items_id", "p_account_id")
		db_table = "fin_accounts"

class Fin_Transactions(models.Model):
	item_accounts_id = models.ForeignKey(Fin_Accounts, db_column='item_accounts_id', on_delete=models.PROTECT)
	p_account_owner = models.CharField(max_length=250, null=True)
	p_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_category = models.TextField(null=True)
	p_category_id = models.IntegerField(null=True)
	p_date = models.DateTimeField(null=True)
	p_iso_currency_code = models.CharField(max_length=10, default="USD", null=True)
	p_location_address = models.CharField(max_length=250, null=True)
	p_location_city = models.CharField(max_length=100, null=True)
	p_location_lat = models.DecimalField(max_digits=15, decimal_places=10, null=True)
	p_location_lon = models.DecimalField(max_digits=15, decimal_places=10, null=True)
	p_location_state = models.CharField(max_length=100, null=True)
	p_location_store_number  = models.CharField(max_length=100, null=True)
	p_location_zip = models.CharField(max_length=50, null=True)
	p_name = models.CharField(max_length=250, null=True)
	p_payment_meta_by_order_of = models.CharField(max_length=250, null=True)
	p_payment_meta_payee = models.CharField(max_length=250, null=True)
	p_payment_meta_payer = models.CharField(max_length=250, null=True)
	p_payment_meta_payment_method = models.CharField(max_length=250, null=True)
	p_payment_meta_payment_processor = models.CharField(max_length=250, null=True)
	p_payment_meta_ppd_id = models.CharField(max_length=250, null=True)
	p_payment_meta_reason = models.CharField(max_length=250, null=True)
	p_payment_meta_reference_number = models.CharField(max_length=250, null=True)
	p_pending = models.NullBooleanField()
	p_pending_transaction_id = models.CharField(max_length=250, null=True)
	p_transaction_id = models.CharField(max_length=250, null=True)
	p_transaction_type = models.CharField(max_length=100, null=True)
	p_unofficial_currency_code = models.CharField(max_length=50, null=True)
	removed = models.IntegerField(default=0, null=True)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ("item_accounts_id", "p_transaction_id")
		db_table = "fin_transactions"

	def get_category(self):
		a=''
		for x in json.loads(self.p_category):
			a += x + ' / '
		return a.rstrip(' / ')

class User_Actions(models.Model):
	user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.PROTECT)
	user_ip = models.CharField(max_length=15)
	action = models.CharField(max_length=50, null=True)
	institution_id = models.CharField(max_length=250, null=True)
	institution_name = models.CharField(max_length=250, null=True)
	error_code = models.CharField(max_length=100, null=True)
	error_message = models.CharField(max_length=250, null=True)
	p_link_session_id = models.CharField(max_length=250, null=True)
	date_created = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "user_actions"

class Users_With_Linked_Institutions(models.Model):
	user_id = models.OneToOneField(User, db_column='user_id', on_delete=models.PROTECT)
	date_created = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "users_with_linked_institutions"

class Plaid_Link_Logs(models.Model):
	user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.PROTECT)
	user_ip = models.CharField(max_length=15)
	p_eventName = models.CharField(max_length=250, null=True)
	p_error_code = models.CharField(max_length=250, null=True)
	p_error_message = models.CharField(max_length=250, null=True)
	p_error_type = models.CharField(max_length=250, null=True)
	p_exit_status = models.CharField(max_length=250, null=True)
	p_institution_id = models.CharField(max_length=250, null=True)
	p_institution_name = models.CharField(max_length=250, null=True)
	p_institution_search_query = models.TextField(null=True)
	p_link_session_id = models.CharField(max_length=250, null=True)
	p_mfa_type = models.CharField(max_length=100, null=True)
	p_request_id = models.CharField(max_length=250, null=True)
	p_timestamp = models.CharField(max_length=30, null=True)
	p_view_name = models.CharField(max_length=100, null=True)
	date_created = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "plaid_link_logs"

class Plaid_Webhook_Logs(models.Model):
	remote_ip = models.CharField(max_length=15, null=True)
	p_webhook_type = models.CharField(max_length=100, null=True)
	p_webhook_code = models.CharField(max_length=100, null=True)
	p_item_id = models.CharField(max_length=250, null=True)
	p_error = JSONField(default=my_default, null=True)
	p_new_transactions = models.IntegerField(null=True)
	p_removed_transactions = models.TextField(null=True)
	p_raw_payload = JSONField(default=my_default, null=True)
	processed = models.IntegerField(default=0)
	date_created = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "plaid_webhook_logs"
