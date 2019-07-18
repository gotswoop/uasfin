# python3 manage.py shell < _analyze_inactive_users.py
import csv
from django.contrib.auth.models import User
from fin.models import Fin_Items, Plaid_Link_Logs

title = 'Activity of users that consented, setup their acccounts on UASFin, but did not link a financial institution'
csv_file = 'uasfin_user_dropoff.csv'

users = User.objects.exclude(last_login=None).filter(is_active=1,id__gt=1005)
with open(csv_file, 'w', newline='') as csvFile:
	writer = csv.writer(csvFile)
	writer.writerow([title])
	writer.writerow([])	
	writer.writerow(["uasfin_id", "session #", "timestamp", "event_name", "view_name", "institution_name", "search_query", "error_code", "error_message", "error_type", "exit_status", "mfa_type"])
	for user in users:

		consent = user.user_treatments.consent
		
		account_setup = 1
		if user.last_login == None:
			account_setup = 0

		linked_bank = 0
		inst_count = Fin_Items.objects.filter(user_id=user,deleted=0).count()
		if inst_count:
			linked_bank = 1

		if consent == 1 and linked_bank == 0 and account_setup ==1:
			
			logs = Plaid_Link_Logs.objects.filter(user_id=user).order_by('id')
			if logs:
				old_session = ''
				session = 0
				for log in logs:
					if old_session != log.p_link_session_id:
						session = session + 1
					writer.writerow([user.id, 'session_'+str(session), log.p_timestamp.replace('T', ' ').replace('Z', '')[:19], log.p_eventName, log.p_view_name, log.p_institution_name, log.p_institution_search_query, log.p_error_code, log.p_error_message, log.p_error_type, log.p_exit_status, log.p_mfa_type])
					old_session = log.p_link_session_id
			else:
				writer.writerow([user.id])
			writer.writerow([])
csvFile.close()
