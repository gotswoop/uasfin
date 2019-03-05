import json

from django.db import models
from django.contrib.auth.models import User

class Items(models.Model):
	user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.CASCADE)
	p_access_token = models.CharField(max_length=100)
	p_item_id = models.CharField(max_length=100)
	p_institution_id = models.CharField(max_length=20)
	p_item_name = models.CharField(max_length=50)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(null=True, auto_now=True)
	past_tokens = models.IntegerField(default=0)
	active = models.IntegerField(default=1)

	class Meta:
		unique_together = ("user_id", "p_institution_id")

class Item_accounts(models.Model):
	items_id = models.ForeignKey(Items, db_column='items_id', on_delete=models.CASCADE)
	p_account_id = models.CharField(max_length=100)
	p_account_balance_available = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_account_balance_current = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_account_balance_iso_currency_code = models.CharField(max_length=5, default="USD")
	p_account_balance_limit = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_account_balance_unofficial_currency_code = models.CharField(max_length=5, null=True)
	p_account_mask = models.CharField(max_length=5, null=True)
	p_account_name = models.CharField(max_length=100, null=True)
	p_account_official_name = models.CharField(max_length=200, null=True)
	p_account_subtype = models.CharField(max_length=20, null=True)
	p_account_type = models.CharField(max_length=20, null=True)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(null=True, auto_now=True)
	
	class Meta:
		unique_together = ("items_id", "p_account_id")

class Item_account_transactions(models.Model):
	item_accounts_id = models.ForeignKey(Item_accounts, db_column='item_accounts_id', on_delete=models.CASCADE)
	p_account_id = models.CharField(max_length=100) ## TODO: GET RID OF THIS
	p_account_owner = models.CharField(max_length=50, null=True)
	p_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True)
	p_category = models.TextField(null=True)
	p_category_id = models.IntegerField(null=True)
	p_date = models.DateTimeField(null=True)
	p_iso_currency_code = models.CharField(max_length=5, default="USD")
	p_location_address = models.CharField(max_length=50, null=True)
	p_location_city = models.CharField(max_length=50, null=True)
	p_location_lat = models.DecimalField(max_digits=15, decimal_places=10, null=True)
	p_location_lon = models.DecimalField(max_digits=15, decimal_places=10, null=True)
	p_location_state = models.CharField(max_length=10, null=True)
	p_location_store_number  = models.CharField(max_length=10, null=True)
	p_location_zip = models.CharField(max_length=10, null=True)
	p_name = models.CharField(max_length=100, null=True)
	p_payment_meta_by_order_of = models.CharField(max_length=50, null=True)
	p_payment_meta_payee = models.CharField(max_length=50, null=True)
	p_payment_meta_payer = models.CharField(max_length=50, null=True)
	p_payment_meta_payment_method = models.CharField(max_length=50, null=True)
	p_payment_meta_payment_processor = models.CharField(max_length=50, null=True)
	p_payment_meta_ppd_id = models.CharField(max_length=50, null=True)
	p_payment_meta_reason = models.CharField(max_length=50, null=True)
	p_payment_meta_reference_number = models.CharField(max_length=50, null=True)
	p_pending = models.BooleanField(default=False)
	p_pending_transaction_id = models.CharField(max_length=100, null=True)
	p_transaction_id = models.CharField(max_length=100, null=True)
	p_transaction_type = models.CharField(max_length=50, null=True)
	p_unofficial_currency_code = models.CharField(max_length=5, null=True)
	removed = models.IntegerField(default=0)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(null=True, auto_now=True)

	class Meta:
		unique_together = ("item_accounts_id", "p_transaction_id")

	def get_category(self):
		a=''
		for x in json.loads(self.p_category):
			a += x + ' / '
		return a.rstrip(' / ')
