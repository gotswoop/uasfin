# python3 manage.py shell < _export_call_list.py

from django.contrib.auth.models import User
from fin.models import Fin_Items

users = User.objects.filter(is_active=1,id__gt=1005)
print("TRUNCATE TABLE uas.plaid_call;")
for user in users:

	consent = user.user_treatments.consent
	if consent == None:
		consent = 'NULL'
	
	account_setup = 1
	if user.last_login == None:
		account_setup = 0

	linked_bank = 0
	inst_count = Fin_Items.objects.filter(user_id=user,deleted=0).count()
	if inst_count:
		linked_bank = 1

	sql = 'INSERT INTO plaid_call (rtid, consent, account_setup, linked_bank, treatment, reward_link, reward_monthly) VALUES(' + user.username + ', ' + str(consent) + ', ' + str(account_setup) + ', ' + str(linked_bank) + ', ' + str(user.user_treatments.treatment.pk) + ', "$' + str(user.user_treatments.treatment.reward_link) + '", "$' +  str(user.user_treatments.treatment.reward_monthly) + '");'
	print(sql)
