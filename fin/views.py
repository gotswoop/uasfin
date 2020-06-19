#import base64
#import os
#import time
import plaid
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

from datetime import datetime, timedelta

from fin.models import Fin_Items, Fin_Accounts, Fin_Accounts_History, Fin_Transactions, Plaid_Link_Logs, Plaid_Webhook_Logs, User_Actions, Users_With_Linked_Institutions
from fin.functions import *
from users.models import User_Treatments, Treatments

client = plaid.Client(client_id=settings.PLAID_CLIENT_ID, secret=settings.PLAID_SECRET, public_key=settings.PLAID_PUBLIC_KEY, environment=settings.PLAID_ENV, api_version='2018-05-22')

# ------------------------------------------------------------------
# Plaid Link event - onEvent
# TODO: Dont' return anything
# TODO: catch insert errors?
# ------------------------------------------------------------------
@login_required()
@require_http_methods(["POST"])
def plaid_link_onEvent(request):
    eventName = request.POST.get('eventName', '')
    metadata = request.POST.get('metadata', '')
    # TODO: json loads will fail if metadata is empty
    metadata = json.loads(metadata)
    
    new_plaid_link_log = Plaid_Link_Logs.objects.create(
        user_id = request.user,
        user_ip = request.META.get('REMOTE_ADDR'),
        p_eventName = eventName,
        p_error_code = metadata.get('error_code'),
        p_error_message = metadata.get('error_message'),
        p_error_type = metadata.get('error_type'),
        p_exit_status = metadata.get('exit_status'),
        p_institution_id = metadata.get('institution_id'),
        p_institution_name = metadata.get('institution_name'),
        p_institution_search_query = metadata.get('institution_search_query'),
        p_link_session_id = metadata.get('link_session_id'),
        p_mfa_type = metadata.get('mfa_type'),
        p_request_id = metadata.get('request_id'),
        p_timestamp = metadata.get('timestamp'),
        p_view_name = metadata.get('view_name'),
    )
    # return JsonResponse({'data': serializers.serialize('json', [new_plaid_link_log])})
    return HttpResponse('')


# ------------------------------------------------------------------
# Plaid Link onExit event
# ------------------------------------------------------------------
@login_required()
@require_http_methods(["POST"])
def plaid_link_onExit(request):
    error = request.POST.get('error', '')
    metadata = request.POST.get('metadata', '')
    
    next_question = request.POST.get('next_question', '')
    question_response = 'Exit'

	# Save user's Exit action
    action = 'lnkScrn:' + next_question + ':' + question_response
    log_user_actions(request, action, None, None, None, None, None)

    error = json.loads(error)
    metadata = json.loads(metadata)

    # Insert into user_actions
    if error == None:
    	new_action = User_Actions.objects.create(
        	user_id = request.user,
        	user_ip = request.META['REMOTE_ADDR'],
        	action = "link_exit",
        	error_code = "USER_EXITED_PLAID_LINK",
        	p_link_session_id = metadata['link_session_id']
    	)
    else:
        new_action = User_Actions.objects.create(
        	user_id = request.user,
        	user_ip = request.META['REMOTE_ADDR'],
        	action = "link_exit",
        	institution_id = metadata['institution']['institution_id'],
        	institution_name = metadata['institution']['name'],
        	error_code = "INVALID_CREDENTIALS",
        	error_message = "The provided credentials were not correct. Please try again.",
        	p_link_session_id = metadata['link_session_id']
    	)
    
    # Dont' return anything
    # return JsonResponse({'error': error, 'metadata': metadata})
    return HttpResponse('')

# ------------------------------------------------------------------
# Link Account (Plaid Link accout page that embeds ifram with instructions on right )
# ------------------------------------------------------------------
@login_required()
def link_account(request):

	# Fetching number of institutions a user has.
	number_of_items = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count()

	treatment = fetch_treatment(request.user.id)
	if not treatment:
		return HttpResponse(status=500)

	context = {
		'title': "Link Institution",
		'items': number_of_items,
		'treatment': treatment,
		'next_question': None,
		'plaid_linkbox_title': None,
		'linkbox_text': None,
	}
	return render(request, 'fin/link_1.html', context)


# ------------------------------------------------------------------
# Link iframe (Plaid Link iframe code)
# ------------------------------------------------------------------
@login_required()
def link_iframe(request, next_question=""):

    # Configuring the webhook here..
    webhook_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/' + settings.PLAID_WEBHOOK_URL

    context = {
	    'title': "Link iFrame",
        'plaid_public_key': settings.PLAID_PUBLIC_KEY,
	    'plaid_environment': settings.PLAID_ENV,
	    'plaid_products': settings.PLAID_PRODUCTS,
	    'plaid_webhook_url': webhook_url,
	    'next_question': next_question,
    }

    return render(request, 'fin/link_0_iframe.html', context)

# ------------------------------------------------------------------
# Re-Link account (Plaid Link page for re-linking)
# ------------------------------------------------------------------
@login_required()
def relink_account(request, item_id):

    try:
    	# Only inactive accounts can be "re-linked"
        # item = Fin_Items.objects.exclude(inactive = 0).exclude(deleted = 1).get(id = item_id, user_id = request.user)
        item = Fin_Items.objects.exclude(deleted = 1).get(id = item_id, user_id = request.user)
    except Fin_Items.DoesNotExist:
       	messages.warning(request, format('Invalid Operation.'))
        return redirect('home')

    # Handle this
    try:
        # Generating public_token
        response = client.Item.public_token.create(item.p_access_token)
    except plaid.errors.PlaidError as e:
        return JsonResponse(format_error(e))

    # log to plaid_api_logs
    
    # Configuring the webhook here..
    webhook_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/' + settings.PLAID_WEBHOOK_URL
    context = {
	    'title': "Re-Link Institution",
        'plaid_public_key': settings.PLAID_PUBLIC_KEY,
        'plaid_environment': settings.PLAID_ENV,
        'plaid_products': settings.PLAID_PRODUCTS,
        'plaid_webhook_url': webhook_url,
        'public_token': response['public_token'],
        'item_id': item_id,
    }
    return render(request, 'fin/relink.html', context)
    
# ------------------------------------------------------------------
# Re-Link onExit
# ------------------------------------------------------------------
@login_required()
@require_http_methods(["POST"])
def plaid_relink_onExit(request):
	error = request.POST.get('error', '')
	error = json.loads(error)
	metadata = request.POST.get('metadata', '')
	metadata = json.loads(metadata)
	item_id = request.POST.get('item_id', 0)
	
	'''
	if not isinstance(item_id, int):
		print(type(item_id))
		messages.warning(request, format('Invalid Operation.'))
		return HttpResponse('')
	'''
	# Insert into user_actions
	if error == None:
		new_action = User_Actions.objects.create(
			user_id = request.user,
			user_ip = request.META['REMOTE_ADDR'],
			action = "relink_item",
			p_link_session_id = metadata['link_session_id']
		)

		try:
			item_obj = Fin_Items.objects.exclude(deleted = 1).get(id = item_id, user_id = request.user)
		except Fin_Items.DoesNotExist:
			messages.warning(request, format('Opps. Something bad happended. We are working on it.'))
			return redirect('home')

		item_obj.inactive = 0
		item_obj.save()
	else:
		new_action = User_Actions.objects.create(
			user_id = request.user,
			user_ip = request.META['REMOTE_ADDR'],
			action = "relink_exit",
			institution_id = metadata['institution']['institution_id'],
			institution_name = metadata['institution']['name'],
			error_code = "INVALID_CREDENTIALS",
			error_message = "The provided credentials were not correct. Please try again.",
			p_link_session_id = metadata['link_session_id']
		)

	# Dont' return anything
	# return JsonResponse({'error': error, 'metadata': metadata})
	return HttpResponse('')

# ------------------------------------------------------------------
# Link account results
# TODO: Only show this page if REFERRER = '/link/'    
# ------------------------------------------------------------------
@login_required()
def link_account_result(request):

	accounts = None
	referer_url = request.META.get('HTTP_REFERER')
	check_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/link/'
    
	number_of_items = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count()
    
	recent_action = User_Actions.objects.filter(user_id = request.user, action__in=["link_item", "link_exit", "relink_item"]).order_by('-date_created').first()

	# Fetching the linking event (link_checking, link_savings etc) that the user exited from by hitting the X in Plaid Link
	last_link_exit_event = User_Actions.objects.filter(user_id = request.user, action__startswith="lnkScrn", action__endswith="Exit").order_by('-date_created')[:1]
	if last_link_exit_event:
		last_action = last_link_exit_event[0].action
		# Splitting the string in the format lnkScrn:link_checking:Exit
		q = last_action.split(':')
		next_question = q[1]
	else:
		next_question = None

	first_timer = 1
	if Users_With_Linked_Institutions.objects.filter(user_id = request.user).count():
		first_timer = 0

	if recent_action.institution_id:
		try:	
			item_id = Fin_Items.objects.exclude(deleted=1).get(user_id=request.user, p_institution_id=recent_action.institution_id)
		except Fin_Items.DoesNotExist:
			item_id = None

		if item_id:
			accounts = Fin_Accounts.objects.filter(item_id=item_id)
    
	# Redirect to dashboard if there are no items OR there were no recent actions.
	if recent_action == None and number_of_items == 0:
		return redirect('home')
    
	treatment = fetch_treatment(request.user.id)
	if not treatment:
		return HttpResponse(status=500)

	context = {
		'title': 'Link Account - Result',
		'items': number_of_items,
		'recent_action': recent_action,
		'accounts': accounts,
		'treatment': treatment,
		'first_timer': first_timer,
		'next_question': next_question,
	}
	return render(request, 'fin/link_2_result.html', context)
    

# ------------------------------------------------------------------
# Link account view - Summary
# ------------------------------------------------------------------
@login_required()
def link_account_summary(request):
   
    referer_url = request.META.get('HTTP_REFERER')
    check_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/link/result/'
    
    # If refererer NOT /link/result/, then redirect to home page    
    if referer_url != check_url:
        messages.warning(request, format('Invalid Operation.'))
        return redirect('home')

    context = {'title': 'Link Account - Summary'}
    return render(request, 'fin/link_3_summary.html')
    
# ------------------------------------------------------------------
# Link account view - Thank You
# ------------------------------------------------------------------
@login_required()
def link_account_thankyou(request):
    
    referer_url = request.META.get('HTTP_REFERER')   
    check_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/link/summary/'
    
    # If refererer NOT /link/summary/, then redirect to home page    
    if referer_url != check_url:
        # messages.warning(request, format('Invalid Operation.'))
        return redirect('home')
    
    if Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count():
        updated_item, new_item = Users_With_Linked_Institutions.objects.update_or_create(user_id = request.user, defaults={'user_id': request.user})
    
    context = {'title': 'Link Account - Thank You'}
    return render(request, 'fin/link_4_thankyou.html')


# ------------------------------------------------------------------
# Site home / dashboard
# ------------------------------------------------------------------
@login_required()
def home(request):

	items = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).order_by('p_item_name')

	treatment = fetch_treatment(request.user.id)
	if not treatment:
		return HttpResponse(status=500)

	context = {
		'title': "Dashboard",
		'items': items,
		'treatment': treatment,
	}

	if items:
		return render(request, 'fin/dashboard.html', context)
	else:
		return render(request, 'fin/dashboard_empty.html', context)

# ------------------------------------------------------------------
# HELP
# ------------------------------------------------------------------
def help(request):
	# return HttpResponse('<h1>Help form</h1>')
	return render(request, 'fin/help.html', {"title": "Help"})

# ------------------------------------------------------------------
# Plaid Link event - onSuccess
# ------------------------------------------------------------------
@require_http_methods(["POST"])
def plaid_link_onSuccess(request):
  
	public_token = request.POST.get('public_token', '')
	metadata = request.POST.get('metadata', '')
	next_question = request.POST.get('next_question', '')
	question_response = 'Success'
	
	# TODO: This will fail if metadata is blank
	metadata = json.loads(metadata)

	try:
		exchange_response = client.Item.public_token.exchange(public_token)
	except plaid.errors.PlaidError as e:
		msg = '# ERROR: Plaid Error @ client.Item.public_token.exchange = ' + str(public_token) + '. Details' + format(e)
		error_handler(msg)
		return HttpResponse(status=500)

	access_token = exchange_response.get('access_token') 
	# TODO - Log to plaid_api_logs
	# msg = 'New item 1 of 4: ' + json.dumps(exchange_response)
	# error_handler(msg)

	# Fetch item info using token
	try:
		item_response = client.Item.get(access_token)
	except plaid.errors.PlaidError as e:
		msg = '# ERROR: Plaid Error @ client.Item.get = ' + str(access_token) + '. Details' + format(e)
		error_handler(msg)
		return HttpResponse(status=500)
	
	# TODO - Log to plaid_api_logs -  json.dumps(item_response))

	# Fetch detailed item info using item institution id
	try:
		institution_response = client.Institutions.get_by_id(item_response.get('item').get('institution_id'))
	except plaid.errors.PlaidError as e:
		msg = '# ERROR: Plaid Error @ client.Institutions.get_by_id = ' + str(item_response.get('item').get('institution_id')) + '. Details' + format(e)
		error_handler(msg)
		return HttpResponse(status=500)
	
	# TODO: log to database - json.dumps(institution_response))

	try:
		fin_item, item_created = Fin_Items.objects.get_or_create(user_id = request.user, p_institution_id = item_response.get('item').get('institution_id'), 
			defaults={
				'p_access_token': access_token, 
				'p_item_id': exchange_response.get('item_id'),
				'p_item_name': institution_response.get('institution').get('name')
			},
		)
	except IntegrityError as e:
		msg = '# ERROR - fin_items insert/lookup: ' + e.args
		error_handler(msg)
		return HttpResponse(status=500)
	
	if item_created is False:
		
		if fin_item.deleted == 1:
			err_code = 'DUPLICATE_INSTITUTION_PREVIOUSLY_DELETED'
			err_message = 'Institution previously linked and deleted'
		else:
			err_code = 'DUPLICATE_INSTITUTION'
			err_message = 'Institution already linked'
		
		log_user_actions(request, "link_item", item_response.get('item').get('institution_id'), institution_response.get('institution').get('name'), 
			err_code, err_message, metadata.get('link_session_id'))
		
		return HttpResponse(status=200)

	else:
		
		log_user_actions(request, "link_item", item_response.get('item').get('institution_id'), institution_response.get('institution').get('name'), 
			None, None, metadata.get('link_session_id'))
		if next_question:
			action = 'lnkScrn:' + next_question + ':' + question_response
			log_user_actions(request, action, None, None, None, None, None)
		
		# Get item_accounts and insert into database.
		try:
			accounts_response = client.Accounts.get(access_token)
		except plaid.errors.PlaidError as e:
			msg = '# ERROR: Plaid Error @ client.Accounts.get = ' + str(access_token) + '. Details' + format(e)
			error_handler(msg)
			return HttpResponse(status=500)
  
		if accounts_response:
			if accounts_response.get('item').get('error') is not None:
				msg = 'Could not find accounts for item_id ' + fin_item.id
				error_handler(msg)
			else:
				accounts = accounts_response.get('accounts')
				for account in accounts:
					new_account = Fin_Accounts.objects.create(
						item_id = fin_item,
						p_account_id = account.get('account_id'),
						p_balances_available = account.get('balances').get('available'),
						p_balances_current = account.get('balances').get('current'),
						p_balances_iso_currency_code = account.get('balances').get('iso_currency_code'),
						p_balances_limit = account.get('balances').get('limit'),
						p_balances_unofficial_currency_code = account.get('balances').get('unofficial_currency_code'),
						p_mask = account.get('mask'),
						p_name = account.get('name'),
						p_official_name = account.get('official_name'),
						p_subtype = account.get('subtype'),
						p_type = account.get('type')
					)
					fin_accounts_history = Fin_Accounts_History.objects.create(
						item_id = fin_item,
						p_account_id = account.get('account_id'),
						p_balances_available = account.get('balances').get('available'),
						p_balances_current = account.get('balances').get('current'),
						p_balances_iso_currency_code = account.get('balances').get('iso_currency_code'),
						p_balances_limit = account.get('balances').get('limit'),
						p_balances_unofficial_currency_code = account.get('balances').get('unofficial_currency_code'),
						p_mask = account.get('mask'),
						p_name = account.get('name'),
						p_official_name = account.get('official_name'),
						p_subtype = account.get('subtype'),
						p_type = account.get('type')
					)

		return HttpResponse(status=200)
									
# ------------------------------------------------------------------
# WEBHOOK - Incoming connection
# ------------------------------------------------------------------
@require_http_methods(["POST"])
@csrf_exempt
def webhook(request):
	incoming = {}
	# incoming = json.loads(request.body.decode('UTF-8')) # decode needed for python < 3.6
	incoming = json.loads(request.body)
	
	# Logging incoming webhook into database
	log_incoming_webhook(incoming, request.META.get('REMOTE_ADDR'))
	
	webhook_type = incoming.get('webhook_type')
	webhook_code = incoming.get('webhook_code')

	# TODO: Only handling webhook_type of TRANSCTIONS and ITEM. item_id for other type of webhooks
	if webhook_type not in ["TRANSACTIONS", "ITEM"]:
		msg = '# TODO - Webhook. Type not yet handled. ' + webhook_type
		error_handler(msg)
		return HttpResponse(status=200)
	
	
	item_id = incoming.get('item_id')
	
	try:	
		item = Fin_Items.objects.exclude(deleted = 1).get(p_item_id = item_id)
	except Fin_Items.DoesNotExist:
		msg ='# WARN - Webhook. No corresponding item_id in fin_items table. ' + json.dumps(incoming)
		error_handler(msg)
		return HttpResponse(status=200)
	
	# TODO: Check other webhook_types and only if ERROR is NONE
	if webhook_type == "TRANSACTIONS":

		response = None

		if webhook_code in ["INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"]:
			# Fetching Transactions
			response = fetch_transactions_from_plaid(client, item)
		elif webhook_code == "TRANSACTIONS_REMOVED":
			# Removing Transactions
			transaction_ids_to_remove = incoming.get('removed_transactions')
			removed_count = Fin_Transactions.objects.filter(**{'p_transaction_id__in': transaction_ids_to_remove}).update(removed = 1)
			if not isinstance(removed_count, int):
				response = "TRANSACTION_REMOVE_NOT_OK"
		else:
			# Unhandled cases
			msg = '# ERROR - Webook (TRANSACTIONS). Should not be in here. ' + webhook_code + ' - ' + str(item_id)
			error_handler(msg)

		# Setting the fin_items.item_refresh_date to now
		if response == None:
			item.item_refresh_date = datetime.now()
			item.save(update_fields=['item_refresh_date'])
		else:
			msg = '# ERROR - Webook (TRANSACTIONS) Webook Code' + webhook_code + ' Item id ' + str(item_id)  + ' Details:' + response
			error_handler(msg)
			return response

	elif webhook_type == "ITEM":

		if webhook_code == "ERROR":
			item.inactive = 1
			item.inactive_date = datetime.now()
			item.inactive_status = incoming.get('error').get('error_code')
			item.save(update_fields=['inactive', 'inactive_date','inactive_status'])
		elif webhook_code == "WEBHOOK_UPDATE_ACKNOWLEDGED":                
			msg = '# TODO - Webhook (ITEM). Webook update acknowleded ' + webhook_code + ' - ' + str(item_id)
			error_handler(msg)
		else:
			# Unhandled cases
			msg = '# ERROR - Webook (ITEM). Should not be in here. ' + webhook_code + ' - ' + str(item_id)
			error_handler(msg)

	return HttpResponse(status=200)

# ------------------------------------------------------------------
# Account details view for a specific item id
# ------------------------------------------------------------------
@login_required()
def account_details(request, item_id):
	
	# TODO Remove this.
	if request.user.is_superuser:
		try:
			item = Fin_Items.objects.exclude(deleted = 1).get(id = item_id)
		except Fin_Items.DoesNotExist:
			messages.warning(request, format('Invalid operation. ! Exists.'))
			return redirect('home')
	else:
		# Checking if viewing user is owner of the account -> item_id
		try:
			item = Fin_Items.objects.exclude(deleted = 1).get(id = item_id, user_id = request.user)
		except Fin_Items.DoesNotExist:
			# messages.warning(request, format('Invalid operation. ! Authorized.'))
			return redirect('home')

	# Maybe no need to check this as already verifying above?
	# accounts = Fin_Accounts.objects.filter(item_id = item_id, item_id__user_id=request.user).exclude(item_id__deleted=1).order_by('p_name')
	accounts = Fin_Accounts.objects.filter(item_id = item_id).exclude(item_id__deleted=1).order_by('p_name')
	
	context = {
		'item': item,
		'accounts': accounts
		}
	return render(request, 'fin/account.html', context)     

# ------------------------------------------------------------------
# Transactions detail page for a specific account
# ------------------------------------------------------------------
@login_required()
def account_transactions(request, item_id, account_id):

	# TODO Remove this.
	if request.user.is_superuser:
		try:
			# account_info = Fin_Accounts.objects.get(id = account_id)
			account_info = Fin_Accounts.objects.exclude(item_id__deleted=1).get(id = account_id, item_id = item_id)
		except Fin_Accounts.DoesNotExist:
			messages.warning(request, format('Invalid operation. ! Exists.'))
			return redirect('home')

	else:
		# Checking if viewing user is owner of the account -> item_id	
		try:
			# account_info = Fin_Accounts.objects.get(id = account_id)
			account_info = Fin_Accounts.objects.exclude(item_id__deleted=1).get(id = account_id, item_id__user_id=request.user, item_id = item_id)
		except Fin_Accounts.DoesNotExist:
			# messages.warning(request, format('Invalid operation. ! Authorized.'))
			return redirect('home')

	
	# No need to check as we are already verifying the user above?
	# transactions = Fin_Transactions.objects.filter(account_id = account_id, account_id__item_id = item_id, account_id__item_id__user_id=request.user).exclude(account_id__item_id__deleted=1).order_by('-p_date')[:60000]
	# Only showing last 6 months of transactions (183days)
	past_months = datetime.today() - timedelta(days=183)
	transactions = Fin_Transactions.objects.exclude(removed=1).exclude(p_pending=1).filter(p_date__gte= past_months).filter(account_id = account_id, account_id__item_id = item_id).exclude(account_id__item_id__deleted=1).order_by('-p_date')

	context = {
		'account': account_info,
		'transactions': transactions
	}
	return render(request, 'fin/transactions.html', context)


# ------------------------------------------------------------------
# Unlink Account
# ------------------------------------------------------------------
@login_required()
def unlink_account(request, item_id):
	
	'''
	# Uncomment if you only want to allow members of CESR TEAM to unlink accounts
	# Check if authorized to delete. Only members of cesr_team can delete accounts
	if not request.user.groups.filter(name='cesr_team').exists():
		messages.warning(request, format('Only staff can unlink accounts.'))
		return redirect('profile')
	'''
    
	try:
		# Checking if user deleting is the owner
		item = Fin_Items.objects.exclude(deleted = 1).get(id = item_id, user_id = request.user)
	except Fin_Items.DoesNotExist:
		item = None
        
	if not item:
		# messages.warning(request, format('Cannot delete. Not the owner.'))
		return redirect('profile')

	# POST REQUEST
	if request.method == "POST":
		unlink_item = request.POST.get('unlink', 0)

		try:
			unlink_item = int(unlink_item)
		except ValueError:
			return HttpResponse(status=500) 

		if unlink_item != item_id:
			messages.warning(request, format('Invalid Operation.'))
			return redirect('profile')

		# TODO - Handle error when item trying to remove is not in Plaid or if access_token is old
		try:
			response = client.Item.remove(item.p_access_token)
		except plaid.errors.PlaidError as e:
			return JsonResponse(format_error(e))

		if response['removed'] == True:
			# Updating Fin_Items and flagging this account as deleted.
			item.p_access_token = None # Setting access_token to null
			item.deleted = 1
			item.deleted_date = datetime.now()
			item.save(update_fields=['p_access_token','deleted','deleted_date'])

			# Recording this event in user actions
			new_action = User_Actions.objects.create(
				user_id = request.user,
				user_ip = request.META.get('REMOTE_ADDR'),
				action = "unlink_item",
				institution_id = item.p_institution_id,
				institution_name = item.p_item_name
			)

		else:
			messages.warning(request, format('Something went wrong. Please report to help desk.'))
			return redirect('profile')
	    
		# Resetting Users_With_Linked_Institutions
		if not Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count():
			Users_With_Linked_Institutions.objects.filter(user_id = request.user).delete()

		messages.success(request, format(item.p_item_name + ' removed.'))
		return redirect('profile')

	# GET request. Show warning page.
	else:
		
		number_of_items = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count()

		treatment = fetch_treatment(request.user.id)
		if not treatment:
			return HttpResponse(status=500)
	
		context = {
			'item_id': item.pk,
			'items': number_of_items,
			'institution_name': item.p_item_name,
			'treatment': treatment,
		}
		return render(request, 'fin/unlink_warning.html', context)
    	
	
# ------------------------------------------------------------------
# Add Account (Plaid Link accout page that embeds ifram with instructions on right )
# ------------------------------------------------------------------
@login_required()
@require_http_methods(["GET", "POST"])
def add_account(request):

	# Fetching number of institutions a user has and treatment
	number_of_items = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count()
	treatment = fetch_treatment(request.user.id)
	if not treatment:
		return HttpResponse(status=500)

	# GET Method
	if request.method == 'GET':

		# Fetch next question
		plaid_linkbox_title, linkbox_text, next_question = next_account_linking_question(request.user.id)
		print(f'Plaid LB title: {plaid_linkbox_title}')
		print(f'Plaid LB text: {linkbox_text}')
		print(f'Next Q: {next_question}')

		item_ids = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).prefetch_related('fin_accounts_set').all()
		context = {
			'title': "Link Institution",
			'items': number_of_items,
			'treatment': treatment,
			'next_question': next_question,
			'plaid_linkbox_title': plaid_linkbox_title,
			'linkbox_text': linkbox_text,
			'item_ids': item_ids,
		}
	
		if next_question == None:
			return render(request, 'fin/link_1.html', context)
		elif next_question == 'q_09_thankyou':
			return render(request, 'fin/q_09_thankyou.html', context)
		elif next_question == 'q_10_end':
			return render(request, 'fin/q_10_end.html', context)
		elif next_question == 'link':
			return render(request, 'fin/link_1.html', context)
		else:
			return render(request, 'fin/add.html', context)	
		
	# POST Method
	elif request.method == 'POST':
		
		question = request.POST.get("question", "")
		question_response = request.POST.get("question_response", "")
		
		# Save user response
		action = 'lnkScrn:' + question + ':' + question_response
		log_user_actions(request, action, None, None, None, None, None)
		
		context = {
			'dummy': None,
		}
		return JsonResponse(context)
	else:
		# TODO
		pass

# Used only by the summary page and all done page
@login_required()
@require_http_methods(["POST"])
def add_account_plus(request):

	if request.method == 'POST':
		
		question = request.POST.get("question", "")
		question_response = request.POST.get("question_response", "")
		
		# Save user response
		action = 'lnkScrn:' + question + ':' + question_response
		log_user_actions(request, action, None, None, None, None, None)
		
		if question_response == 'Finish': # this is from the last page
			# Making an entry in the users_with_linked_institutions table
			updated_item, new_item = Users_With_Linked_Institutions.objects.update_or_create(user_id = request.user, defaults={'user_id': request.user})
			return redirect('home')
		else: # This is from the summary page
			return redirect('add_account')
	else:
		# GET request redirects to home
		return redirect('home')


# ------------------------------------------------------------------
# Reset account - Unline and reset. Used for testing for Fin Health Network and USC
# ------------------------------------------------------------------
@login_required()
def reset_account(request):
	
	# Only allow cesr_team and cfsi_team members
	if not request.user.groups.filter(name__in=['cesr_team','cfsi_team']).exists():
		messages.warning(request, format('Only staff can unlink accounts.'))
		return redirect('profile')
	
	try:
		# Checking if user deleting is the owner
		# Get all items owned by users
		items = Fin_Items.objects.exclude(deleted = 1).filter(user_id = request.user)
	except Fin_Items.DoesNotExist:
		items = None

	# deleteing all accounts
	for item in items:
		try:
			response = client.Item.remove(item.p_access_token)
		except plaid.errors.PlaidError as e:
			print("ARGH!!")
			return JsonResponse(format_error(e))

		if response['removed'] == True:
			# Updating Fin_Items and flagging this account as deleted.
			item.p_access_token = None # Setting access_token to null
			item.deleted = 1
			item.deleted_date = datetime.now()
			item.save(update_fields=['p_access_token','deleted','deleted_date'])

			# Recording this event in user actions
			new_action = User_Actions.objects.create(
				user_id = request.user,
				user_ip = request.META.get('REMOTE_ADDR'),
				action = "unlink_item",
				institution_id = item.p_institution_id,
				institution_name = item.p_item_name
			)
		else:
			messages.warning(request, format('Something went wrong. Please report to help desk.'))
			return redirect('profile')

	Fin_Transactions.objects.filter(account_id__item_id__user_id=request.user).delete()
	Fin_Accounts.objects.filter(item_id__user_id=request.user).delete()
	Fin_Accounts_History.objects.filter(item_id__user_id=request.user).delete()
	Fin_Items.objects.filter(user_id=request.user).delete()
	User_Actions.objects.filter(user_id=request.user).delete()
	Users_With_Linked_Institutions.objects.filter(user_id=request.user).delete()

	messages.warning(request, format('All accounts unlinked and account reset for testing.'))		
	return redirect('home')
