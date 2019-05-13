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
