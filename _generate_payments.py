# python3 manage.py shell < _gen_payament.py
import csv
import sys
import os
from django.conf import settings
from django.contrib.auth.models import User
from fin.models import Fin_Items
from django.db import IntegrityError
from datetime import date, datetime, timedelta
from fin.functions import fetch_treatment
from users.models import User_Treatments

today = datetime.today()
first_day_of_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
prev_month = first_day_of_this_month - timedelta(days=7)
first_day_of_prev_month = prev_month.replace(day=1)

print(first_day_of_prev_month)
print(first_day_of_this_month)

title = 'UASFin2 (Plaid) payment file. Generated on ' + str(date.today())
legend = 'For dates between ' + first_day_of_prev_month.strftime('%Y-%m-%d') + ' and ' + first_day_of_this_month.strftime('%Y-%m-%d')
csv_file = 'uasfin_payment_' + str(date.today()) + '.csv'

users = User.objects.filter(is_active=1,id__gte=1006)

with open(csv_file, 'w', newline='') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow([title])
	writer.writerow([])	
	writer.writerow(["panel_id", "Wave", "Treatment #", "Reward for Linking ($)", "Reward for keeping account active ($)", "New accounts linked", "Total Account", "Accounts Active", "Total Payment ($)"])
	for user in users:
		items = Fin_Items.objects.filter(user_id=user)
		if items:
			treatment = fetch_treatment(user.pk)
			# FIX THIS
			wave = User_Treatments.objects.get(user_id=user).wave
			new_accounts_in_last_month = Fin_Items.objects.filter(user_id=user, date_created__gte=first_day_of_prev_month, date_created__lt=first_day_of_this_month, deleted=0).count()
			total_accounts = Fin_Items.objects.filter(user_id=user, deleted=0).count()
			active_accounts = Fin_Items.objects.filter(user_id=user, inactive=0, deleted=0).count()

			payment = (new_accounts_in_last_month * treatment.reward_link) + (active_accounts * treatment.reward_monthly) 
			writer.writerow([user.username, wave, treatment.treatment, treatment.reward_link, treatment.reward_monthly, new_accounts_in_last_month, total_accounts, active_accounts, payment])
			payment = 0

	writer.writerow([])
	writer.writerow([])
	writer.writerow([legend])
csvFile.close()
