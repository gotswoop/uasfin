#import base64
#import os
from datetime import datetime, timedelta
import plaid
import json
#import time

from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Fin_Items, Fin_Accounts, Fin_Transactions, Plaid_Link_Logs, Plaid_Webhook_Logs, User_Actions, Users_With_Linked_Institutions
from .functions import pretty_print_response, fetch_transactions_from_plaid, log_incoming_webhook, insert_transaction, format_error
from django.conf import settings
from django.contrib import messages
import logging
from django.core import serializers
from django.db.models import Q

access_token = None
client = plaid.Client(client_id=settings.PLAID_CLIENT_ID, secret=settings.PLAID_SECRET, public_key=settings.PLAID_PUBLIC_KEY, environment=settings.PLAID_ENV, api_version='2018-05-22')
logger = logging.getLogger(__name__)

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
	context = {
		'title': "Link Institution",
		'items': number_of_items,
	}
	return render(request, 'fin/link_1.html', context)


# ------------------------------------------------------------------
# Link iframe (Plaid Link iframe code)
# ------------------------------------------------------------------
@login_required()
def link_iframe(request):

    # Configuring the webhook here..
    webhook_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/' + settings.PLAID_WEBHOOK_URL

    context = {
	    'title': "Link iFrame",
        'plaid_public_key': settings.PLAID_PUBLIC_KEY,
	    'plaid_environment': settings.PLAID_ENV,
	    'plaid_products': settings.PLAID_PRODUCTS,
	    'plaid_webhook_url': webhook_url
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

    referer_url = request.META.get('HTTP_REFERER')
    check_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/link/'
    
    number_of_items = Fin_Items.objects.filter(user_id = request.user).exclude(deleted = 1).count()
    
    recent_action = User_Actions.objects.filter(user_id = request.user, action__in=["link_item", "link_exit", "relink_item"]).order_by('-date_created').first()
    
    first_timer = 1
    if Users_With_Linked_Institutions.objects.filter(user_id = request.user).count():
    	first_timer = 0

    # Redirect to dashboard if there are no items OR there were no recent actions.
    if recent_action == None and number_of_items == 0:
    	return redirect('home')
    
    context = {
	    'title': 'Link Account - Result',
	    'items': number_of_items,
        'recent_action': recent_action,
        'first_timer': first_timer
    }
    return render(request, 'fin/link_2_result.html', context)
    

# ------------------------------------------------------------------
# Link account view - Summary
# TODO: remove messages.warning? why tell them?
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
# TODO: remove messages.warning? why tell them?
# TODO: try and catch the SQL 
# TODO: what about duplicates???? Only doing this as I don't know how to do a INSERT IGNORE..
# ------------------------------------------------------------------
@login_required()
def link_account_thankyou(request):
    
    referer_url = request.META.get('HTTP_REFERER')   
    check_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/link/summary/'
    
    # If refererer NOT /link/summary/, then redirect to home page    
    if referer_url != check_url:
        messages.warning(request, format('Invalid Operation.'))
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
  
	context = {
		'title': "Dashboard",
		'items': items
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
# TODO: Don't send access_token and item_id to client
# ------------------------------------------------------------------
@require_http_methods(["POST"])
def plaid_link_onSuccess(request):
  
	global access_token  ## TODO: YIKES
	public_token = request.POST.get('public_token', '')
	metadata = request.POST.get('metadata', '')
	# TODO: This will fail if metadata is blank
	metadata = json.loads(metadata)

	try:
		# Getting "access_token" for the returned "public_token" from Plaid Link
		exchange_response = client.Item.public_token.exchange(public_token)
		## Insert into plaid_api_logs
	except plaid.errors.PlaidError as e:
		return JsonResponse(format_error(e))

	access_token = exchange_response['access_token'] 
	logger.debug("#---------------------------------") # Starting with an empty new line
	logger.debug('New item 1 of 4: ' + json.dumps(exchange_response))

	# Get item info using token
	item_response = client.Item.get(access_token)
	logger.debug('New item 2 of 4: ' + json.dumps(item_response))

	# Get more item info using item institution id
	institution_response = client.Institutions.get_by_id(item_response['item']['institution_id'])
	logger.debug('New item 3 of 4: ' + json.dumps(institution_response))

	try:
		already_exists = Fin_Items.objects.get(user_id = request.user, p_institution_id = item_response['item']['institution_id'])
	except Fin_Items.DoesNotExist:
		already_exists = None

	if already_exists:
		# Return to dashboard if it's a duplicate
		# logger.debug("New item 4 of 4 (DUPLICATE): (user_id - Access_tk - Item_id - Inst_id - Inst_name): " + str(already_exists.user_id) + " - " + already_exists.p_access_token + " - " + already_exists.p_institution_id + " - " + already_exists.p_item_name) ## TODO: Log this into user actions
		logger.debug('New item 4 of 4 (DUPLICATE): ' + serializers.serialize('json', [already_exists]))
		logger.debug("#---------------------------------") # Ending with an empty new line
		# messages.warning(request, format(institution_response['institution']['name']))
		if already_exists.deleted == 1:
			err_code = 'DUPLICATE_INSTITUTION_PREVIOUSLY_DELETED'
		else:
			err_code = 'DUPLICATE_INSTITUTION'
		# TODO: try and catch this??
		new_action = User_Actions.objects.create(
			user_id = request.user,
			user_ip = request.META['REMOTE_ADDR'],
			action = "link_item",
			institution_id = item_response['item']['institution_id'],
			institution_name = institution_response['institution']['name'],
			error_code = err_code,
			error_message = "Institution previously linked",
			p_link_session_id = metadata['link_session_id']
		)

		# return JsonResponse({'error': 'Duplicate', 'auth': exchange_response, 'item': item_response['item'], 'institution': institution_response['institution']})
		return HttpResponse('')
	else:
		# Add record
		# TODO: try and catch this??
		new_item = Fin_Items.objects.create(
			user_id = request.user, 
			p_access_token = access_token, 
			p_item_id = exchange_response['item_id'], 
			p_institution_id = item_response['item']['institution_id'], 
			p_item_name = institution_response['institution']['name'],
		)
		# TODO: try and catch this??
		new_action = User_Actions.objects.create(
			user_id = request.user,
			user_ip = request.META['REMOTE_ADDR'],
			action = "link_item",
			institution_id = item_response['item']['institution_id'],
			institution_name = institution_response['institution']['name'],
			p_link_session_id = metadata['link_session_id']
		)
		# logger.debug("New item 4 of 4 (INSERTED): (user_id - Access_tk - Item_id - Inst_id - Inst_name): " + str(request.user.id) + " - " + new_item.p_access_token + " - " + new_item.p_institution_id + " - " + new_item.p_item_name) ## TODO: Log this into user actions
		logger.debug('New item 4 of 4 (INSERTED): ' + serializers.serialize('json', [new_item]))

		# Get item_accounts and insert into database.
		try:
			accounts_response = client.Accounts.get(access_token)
		except plaid.errors.PlaidError as e:
			return JsonResponse(format(e))
  
		logger.debug('New accounts (raw): ' + json.dumps(accounts_response))

		if accounts_response:
			if accounts_response['item']['error'] is not None:
				logger.error('Could not find accounts for item_id ' + new_item.id)
			else:
				accounts = accounts_response['accounts']
				cnt = 1
				for account in accounts:
					new_account = Fin_Accounts.objects.create(
						items_id = new_item,
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
				logger.debug('New account ' + str(cnt) + ' (INSERTED): ' +  serializers.serialize('json', [new_account]))
				cnt = cnt + 1

		logger.debug("#---------------------------------") # Ending with an empty new line

		# TODO: Don't send access_token and item_id to client
		# return JsonResponse({'error': None, 'auth': exchange_response, 'item': item_response['item'], 'institution': institution_response['institution'], 'duplicate': 0})
		return HttpResponse('')
									
# ------------------------------------------------------------------
# WEBHOOK - Incoming connection
# ------------------------------------------------------------------
# TODO: restrict access to specific subnets
@require_http_methods(["POST"])
@csrf_exempt
def webhook(request):
	incoming = {}
	# Receiving request.body in bytes and converting to a dict
	incoming = json.loads(request.body)
	# incoming = json.loads(request.body.decode('UTF-8')) # decode needed for python < 3.6

	# Logging incoming webhook into database
	log_incoming_webhook(incoming, request.META.get('REMOTE_ADDR'))
	
	webhook_type = incoming.get('webhook_type')
	webhook_code = incoming.get('webhook_code')

	# TODO: Only handling webhook_type of TRANSCTIONS and ITEM
	if webhook_type not in ["TRANSACTIONS", "ITEM"]:
		logger.debug('# TODO - Webhook. Type not yet handled. ' + webhook_type)
		return HttpResponse(status=200)
	
	# There won't be an item_id for other type of webhooks
	item_id = incoming.get('item_id')
	
	try:	
		item = Fin_Items.objects.exclude(deleted = 1).get(p_item_id = item_id)
	except Fin_Items.DoesNotExist:
		logger.debug('# WARN - Webhook. No corresponding item_id in fin_items table. ' + json.dumps(incoming))
		return HttpResponse(status=404)
	
	# TODO: Check other webhook_types and only if ERROR is NONE
	if webhook_type == "TRANSACTIONS":

		response = None

		if webhook_code in ["INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"]:
			# Fetching Transactions
			response = fetch_transactions_from_plaid(client, item, logger)
		elif webhook_code == "TRANSACTIONS_REMOVED":
			# Removing Transactions
			transaction_ids_to_remove = incoming.get('removed_transactions')
			removed_count = Fin_Transactions.objects.filter(**{'p_transaction_id__in': transaction_ids_to_remove}).update(removed = 1)
			if not isinstance(removed_count, int):
				response = "TRANSACTION_REMOVE_NOT_OK"
		else:
			# Unhandled cases
			logger.debug('# ERROR - Webook (TRANSACTIONS). Should not be in here. ' + webhook_code + ' - ' + item_id)

		# Setting the fin_items.item_refresh_date to now
		if response == None:
			item.item_refresh_date = datetime.now()
			item.save(update_fields=['item_refresh_date'])
		else:
			logger.debug('# ERROR - Webook (TRANSACTIONS) Webook Code' + webhook_code + ' Item id ' + item_id  + ' Details:' + response)

	elif webhook_type == "ITEM":

		if webhook_code == "ERROR":
			item.inactive = 1
			item.inactive_date = datetime.now()
			item.inactive_status = incoming.get('error').get('error_code')
			item.save(update_fields=['inactive', 'inactive_date','inactive_status'])
		elif webhook_code == "WEBHOOK_UPDATE_ACKNOWLEDGED":                
			logger.debug('# TODO - Webhook (ITEM). Webook update acknowleded ' + webhook_code + ' - ' + item_id)
		else:
			# Unhandled cases
			logger.debug('# ERROR - Webook (ITEM). Should not be in here. ' + webhook_code + ' - ' + item_id)

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
	# accounts = Fin_Accounts.objects.filter(items_id = item_id, items_id__user_id=request.user).exclude(items_id__deleted=1).order_by('p_name')
	accounts = Fin_Accounts.objects.filter(items_id = item_id).exclude(items_id__deleted=1).order_by('p_name')
	
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
			account_info = Fin_Accounts.objects.exclude(items_id__deleted=1).get(id = account_id, items_id = item_id)
		except Fin_Accounts.DoesNotExist:
			messages.warning(request, format('Invalid operation. ! Exists.'))
			return redirect('home')

	else:
		# Checking if viewing user is owner of the account -> item_id	
		try:
			# account_info = Fin_Accounts.objects.get(id = account_id)
			account_info = Fin_Accounts.objects.exclude(items_id__deleted=1).get(id = account_id, items_id__user_id=request.user, items_id = item_id)
		except Fin_Accounts.DoesNotExist:
			# messages.warning(request, format('Invalid operation. ! Authorized.'))
			return redirect('home')

	
	# No need to check as we are already verifying the user above?
	# transactions = Fin_Transactions.objects.filter(item_accounts_id = account_id, item_accounts_id__items_id = item_id, item_accounts_id__items_id__user_id=request.user).exclude(item_accounts_id__items_id__deleted=1).order_by('-p_date')[:60000]
	# Only showing last 6 months of transactions (183days)
	past_months = datetime.today() - timedelta(days=183)
	transactions = Fin_Transactions.objects.exclude(removed=1).filter(p_date__gte= past_months).filter(item_accounts_id = account_id, item_accounts_id__items_id = item_id).exclude(item_accounts_id__items_id__deleted=1).order_by('-p_date')

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
				user_ip = request.META['REMOTE_ADDR'],
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

		context = {
			'item_id': item.pk,
			'items': number_of_items,
			'institution_name': item.p_item_name
		}
		return render(request, 'fin/unlink_warning.html', context)
    	
	
