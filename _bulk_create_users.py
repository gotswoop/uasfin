# python3 manage.py shell < _bulk_create_users.py
import csv
import sys
import os
from django.conf import settings
from django.contrib.auth.models import User
from users.models import User_Treatments, Treatments
from django.db import IntegrityError

wave = 2
panel_file = 'wave_2a.csv'

with open(panel_file, 'r') as f:
	reader = csv.reader(f)
	for user in reader:
		username = user[0]
		treatment = user[1]
		try:
			treatment_obj = Treatments.objects.get(treatment = treatment)
		except Treatments.DoesNotExist:
			print('Treatment ' + treatment + ' not found')
			sys.exit()

		try:	
			user_obj = User.objects.create_user(username,'uashelp@usc.edu', 'CESRUSC123!!!')
		except IntegrityError as e:
			msg = '# User ' + str(username) + ' already exists ' + str(e.args)
			print(msg)
			continue
			
		user_treatments_obj = User_Treatments.objects.create(user_id = user_obj, treatment = treatment_obj, wave=wave)
		print("Created account " + str(user_obj.username) + ' with treatment ' + str(user_treatments_obj.treatment.treatment))

		cmd = 'python3 manage.py set_tokens ' + username
		os.system(cmd)

'''	
SET FOREIGN_KEY_CHECKS = 0;
delete from auth_user where id > 13;
SET FOREIGN_KEY_CHECKS = 1;
'''
