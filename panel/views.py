import json
import logging

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.core import serializers
from django.contrib.auth.models import User

from datetime import datetime, timedelta

from fin.models import Fin_Items, Fin_Accounts, Fin_Transactions, Plaid_Link_Logs, Plaid_Webhook_Logs, User_Actions, Users_With_Linked_Institutions
from users.models import User_Treatments, Treatments
import xlwt
from django.db.models.functions import Length

@login_required()
# TODO: Decorators??
def panel_home(request):

	# Only allow cesr_team and cfsi_team members
	if not request.user.groups.filter(name__in=['cesr_team','cfsi_team']).exists():
		return redirect('home')

	users_obj = User.objects.all().order_by('-last_login')

	counts = {}	
	# TODO: 1005 is not good!
	counts['invited'] = User.objects.filter(is_active=1, id__gt=1005).count()
	counts['consent_yes'] = User_Treatments.objects.filter(consent=1, user_id__id__gt=1005).count()
	counts['consent_no'] = User_Treatments.objects.filter(consent=0, user_id__id__gt=1005).count()
	counts['consent_dontbankonline'] = User_Treatments.objects.filter(consent=2, user_id__id__gt=1005).count()
	counts['consent_waiting'] = User_Treatments.objects.filter(consent=None, user_id__id__gt=1005).count()
	counts['active'] = Fin_Items.objects.filter(deleted=0, user_id__gt=1005).values('user_id').distinct().count()
	counts['institutions'] = Fin_Items.objects.filter(deleted=0, user_id__gt=1005).count()
	counts['institutions_average'] = round((counts['institutions'] / counts['active']), 1)
	#inactive = User.objects.exclude(last_login=None).filter(fin_items__deleted=0, id__gt=1005, user_treatments__consent=1).values('id').distinct()
	
	cesr_team = False
	if request.user.groups.filter(name__in=['cesr_team']).exists():
		cesr_team = True
	
	context = {
		'title': "Panel Home",
		'users': users_obj,
		'counts': counts,
		'cesr_team': cesr_team,
	}

	return render(request, 'panel/home.html', context)

@login_required()
def panel_admin(request):

	if request.user.username != 'swoop':
		return redirect('home')

	users_obj = User.objects.all().order_by('-last_login')

	counts = {}	
	# TODO: 1005 is not good!
	counts['invited'] = User.objects.filter(is_active=1, id__gt=1005).count()
	counts['consent_yes'] = User_Treatments.objects.filter(consent=1, user_id__id__gt=1005).count()
	counts['consent_no'] = User_Treatments.objects.filter(consent=0, user_id__id__gt=1005).count()
	counts['consent_waiting'] = User_Treatments.objects.filter(consent=None, user_id__id__gt=1005).count()
	counts['active'] = Fin_Items.objects.filter(deleted=0, user_id__gt=1005).values('user_id').distinct().count()
	counts['institutions'] = Fin_Items.objects.filter(deleted=0, user_id__gt=1005).count()
	counts['institutions_average'] = round((counts['institutions'] / counts['active']), 1)
	#inactive = User.objects.exclude(last_login=None).filter(fin_items__deleted=0, id__gt=1005, user_treatments__consent=1).values('id').distinct()
		
	context = {
		'title': "Panel Home",
		'users': users_obj,
		'counts': counts,
	}

	return render(request, 'panel/admin.html', context)

@login_required
def panel_download(request):

	# users = User.objects.annotate(text_len=Length('username')).filter(text_len__gt=6).order_by('-last_login')
	users = User.objects.filter(id__gt=1005).order_by('-last_login')

	response = HttpResponse(content_type='application/ms-excel')
	response['Content-Disposition'] = 'attachment; filename="UASFin_Participation_Data.xls"'

	wb = xlwt.Workbook(encoding='utf-8')
	ws_1 = wb.add_sheet('Active Users')
	ws_2 = wb.add_sheet('Inactive Users')
	ws_3 = wb.add_sheet('No Response')
	ws_4 = wb.add_sheet('No Consent')
	ws_5 = wb.add_sheet('Don\'t Bank Online')

	# Active Users
	# Sheet header, first row
	row_num = 0

	font_style = xlwt.XFStyle()
	font_style.font.bold = True

	columns = ['Panel Id', 'Treatment', 'Wave', 'Consent', 'Last Login', 'Institutions Liked' ]

	for col_num in range(len(columns)):
		ws_1.write(row_num, col_num, columns[col_num], font_style)

	# Sheet body, remaining rows
	font_style = xlwt.XFStyle()

	for user in users:
		if user.fin_items_set.count() > 0:
			row = [
				user.username, 
				str(user.user_treatments.treatment.pk) + ' $' + str(user.user_treatments.treatment.reward_link) + ' / $' + str(user.user_treatments.treatment.reward_monthly),
				user.user_treatments.wave,
				user.user_treatments.get_consent(),
				user.last_login.strftime("%Y-%m-%d"),
				user.fin_items_set.count()
			]
			row_num += 1
			for col_num in range(len(row)):
				ws_1.write(row_num, col_num, row[col_num], font_style)
	
	# Inactive Users
	# Sheet header, first row
	row_num = 0

	font_style = xlwt.XFStyle()
	font_style.font.bold = True

	columns = ['Panel Id', 'Treatment', 'Wave', 'Consent', 'Last Login', 'Institutions Liked' ]

	for col_num in range(len(columns)):
		ws_2.write(row_num, col_num, columns[col_num], font_style)

	# Sheet body, remaining rows
	font_style = xlwt.XFStyle()

	for user in users:
		if (user.fin_items_set.count() == 0) and (user.last_login != None) and (user.user_treatments.consent == 1):
			row = [
				user.username, 
				str(user.user_treatments.treatment.pk) + ' $' + str(user.user_treatments.treatment.reward_link) + ' / $' + str(user.user_treatments.treatment.reward_monthly),
				user.user_treatments.wave,
				user.user_treatments.get_consent(),
				user.last_login.strftime("%Y-%m-%d"),
				'-'
			]
			row_num += 1
			for col_num in range(len(row)):
				ws_2.write(row_num, col_num, row[col_num], font_style)
	

	# No response
	# Sheet header, first row
	row_num = 0

	font_style = xlwt.XFStyle()
	font_style.font.bold = True

	columns = ['Panel Id', 'Treatment', 'Wave', 'Consent', 'Last Login', 'Institutions Liked' ]

	for col_num in range(len(columns)):
		ws_3.write(row_num, col_num, columns[col_num], font_style)

	# Sheet body, remaining rows
	font_style = xlwt.XFStyle()

	for user in users:
		if (user.fin_items_set.count() == 0) and (user.last_login == None) and (user.user_treatments.consent == 1):
			row = [
				user.username, 
				str(user.user_treatments.treatment.pk) + ' $' + str(user.user_treatments.treatment.reward_link) + ' / $' + str(user.user_treatments.treatment.reward_monthly),
				user.user_treatments.wave,
				user.user_treatments.get_consent(),
				'Never',
				'-'
			]
			row_num += 1
			for col_num in range(len(row)):
				ws_3.write(row_num, col_num, row[col_num], font_style)

	# No consent
	# Sheet header, first row
	row_num = 0

	font_style = xlwt.XFStyle()
	font_style.font.bold = True

	columns = ['Panel Id', 'Treatment', 'Wave', 'Consent', 'Last Login', 'Institutions Liked' ]

	for col_num in range(len(columns)):
		ws_4.write(row_num, col_num, columns[col_num], font_style)

	# Sheet body, remaining rows
	font_style = xlwt.XFStyle()

	for user in users:
		if user.user_treatments.consent == 0:
			row = [
				user.username, 
				str(user.user_treatments.treatment.pk) + ' $' + str(user.user_treatments.treatment.reward_link) + ' / $' + str(user.user_treatments.treatment.reward_monthly),
				user.user_treatments.wave,
				user.user_treatments.get_consent(),
				'Never',
				'-'
			]
			row_num += 1
			for col_num in range(len(row)):
				ws_4.write(row_num, col_num, row[col_num], font_style)

	# Don't bank online
	# Sheet header, first row
	row_num = 0

	font_style = xlwt.XFStyle()
	font_style.font.bold = True

	columns = ['Panel Id', 'Treatment', 'Wave', 'Consent', 'Last Login', 'Institutions Liked' ]

	for col_num in range(len(columns)):
		ws_5.write(row_num, col_num, columns[col_num], font_style)

	# Sheet body, remaining rows
	font_style = xlwt.XFStyle()

	for user in users:
		if user.user_treatments.consent == 2:
			row = [
				user.username, 
				str(user.user_treatments.treatment.pk) + ' $' + str(user.user_treatments.treatment.reward_link) + ' / $' + str(user.user_treatments.treatment.reward_monthly),
				user.user_treatments.wave,
				user.user_treatments.get_consent(),
				'Never',
				'-'
			]
			row_num += 1
			for col_num in range(len(row)):
				ws_5.write(row_num, col_num, row[col_num], font_style)
						
	wb.save(response)
	return response
