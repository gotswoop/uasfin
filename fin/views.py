#import base64
#import os
import datetime
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
from .models import Items, Item_accounts, Item_account_transactions, Plaid_Link_Logs, User_Actions, Users_With_Atleast_One_Linked_Institution, Plaid_Webhook_Logs
from .functions import pretty_print_response, fetch_transactions_from_plaid, format_error
from django.conf import settings
from django.contrib import messages
import logging
from django.core import serializers
from django.utils import timezone
import pytz

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
# Link account (Plaid Link page)
# ------------------------------------------------------------------
@login_required()
def link_account(request):

    # Configuring the webhook here..
    webhook_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/' + settings.PLAID_WEBHOOK_URL

    context = {
	    'title': "Link Institution",
        'plaid_public_key': settings.PLAID_PUBLIC_KEY,
	    'plaid_environment': settings.PLAID_ENV,
	    'plaid_products': settings.PLAID_PRODUCTS,
	    'plaid_webhook_url': webhook_url
    }

    return render(request, 'fin/link_1.html', context)

# ------------------------------------------------------------------
# Re-Link account (Plaid Link page for re-linking)
# ------------------------------------------------------------------
@login_required()
def relink_account(request, item_id):

    try:
        item = Items.objects.exclude(deleted = 1).get(id = item_id, user_id = request.user)
    except Items.DoesNotExist:
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
    }
    return render(request, 'fin/relink.html', context)
    

# ------------------------------------------------------------------
# Link account results
# TODO: Only show this page if REFERRER = '/link/'    
# ------------------------------------------------------------------
@login_required()
def link_account_result(request):

    referer_url = request.META.get('HTTP_REFERER')
    check_url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/link/'
    
    number_of_items = Items.objects.filter(user_id = request.user).exclude(deleted = 1).count()
    
    recent_action = User_Actions.objects.filter(user_id = request.user, action__in=["link_item", "link_exit"]).order_by('-date_created').first()
    
    first_timer = 1
    if Users_With_Atleast_One_Linked_Institution.objects.filter(user_id = request.user).count():
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
    
    if Items.objects.filter(user_id = request.user).exclude(deleted = 1).count():
        updated_item, new_item = Users_With_Atleast_One_Linked_Institution.objects.update_or_create(user_id = request.user, defaults={'user_id': request.user})
    
    context = {'title': 'Link Account - Thank You'}
    return render(request, 'fin/link_4_thankyou.html')
    
# ------------------------------------------------------------------
# Site home / dashboard
# ------------------------------------------------------------------
@login_required()
def home(request):

	items = Items.objects.filter(user_id = request.user).exclude(deleted = 1).order_by('p_item_name')
  
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
		already_exists = Items.objects.get(user_id = request.user, p_institution_id = item_response['item']['institution_id'])
	except Items.DoesNotExist:
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
		new_item = Items.objects.create(
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
			return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  
		logger.debug('New accounts (raw): ' + json.dumps(accounts_response))

		if accounts_response:
			if accounts_response['item']['error'] is not None:
				logger.error('Could not find accounts for item_id ' + new_item.id)
			else:
				accounts = accounts_response['accounts']
				cnt = 1
				for account in accounts:
					new_account = Item_accounts.objects.create(
						items_id = new_item,
						p_account_id = account['account_id'],
						p_account_balance_available = account['balances']['available'],
						p_account_balance_current = account['balances']['current'],
						p_account_balance_iso_currency_code = account['balances']['iso_currency_code'],
						p_account_balance_limit = account['balances']['limit'],
						p_account_balance_unofficial_currency_code = account['balances']['unofficial_currency_code'],
						p_account_mask = account['mask'],
						p_account_name = account['name'],
						p_account_official_name = account['official_name'],
						p_account_subtype = account['subtype'],
						p_account_type = account['type']
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
	incoming = json.loads(request.body) 
	# TODO: Handle Special chars??
	# incoming = json.loads(request.body.decode('UTF-8')) # decode needed for python < 3.6

	webhook_type = incoming.get('webhook_type')
	webhook_code = incoming.get('webhook_code')

	# TODO: Only handling webhook_type of TRANSCTIONS and ITEM
	if webhook_type not in ["TRANSACTIONS", "ITEM"]:
		logger.debug('# WARN - Webhook. Type not yet handled. ' + json.dumps(incoming))
		return HttpResponse('')

	try:
		item_id = incoming.get('item_id')
		res = Items.objects.values('p_access_token').exclude(deleted = 1).get(p_item_id = item_id)
		access_token = res.get('p_access_token')
	except Items.DoesNotExist:
		logger.debug('# WARN - Webhook. No corresponding item_id in fin_items table. ' + json.dumps(incoming))
		return HttpResponse('')
	
	# Logging incoming webhook into database
	log_imcoming_webhook(incoming, request.META.get('REMOTE_ADDR'))
	
	# TODO: Check other webhook_types and only if ERROR is NONE
	if webhook_type == "TRANSACTIONS":
		if webhook_code in ["INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"]:
			logger.debug('Getting transactions for item_id = ' + item_id)
			fetch_transactions_from_plaid(access_token)
		elif webhook_code == "TRANSACTIONS_REMOVED":                
			# remove_transactions()
			logger.debug('Rare remove transactions for item_id = ' + item_id)
		else:
			logger.debug('*** Should not be in here. item_id = ' + item_id)
	elif webhook_type == "ITEM":
		if webhook_code == "ERROR":
			logger.debug('Time to update credentials for ' + item_id)
			# Set fin_items.active = 0
		elif webhook_code == "WEBHOOK_UPDATE_ACKNOWLEDGED":                
			# DO NOTHING FOR NOW
			logger.debug('Webhook update acknowleded' + item_id)

	return HttpResponse('')


# ------------------------------------------------------------------
# Account details view for a specific item id
# ------------------------------------------------------------------
@login_required()
def account_details(request, item_id):
	
    try:
        # TODO: Limit 60 days of transactions
        accounts = Item_accounts.objects.filter(items_id = item_id, items_id__user_id=request.user).exclude(items_id__deleted=1).order_by('p_account_name')
    except Item_accounts.DoesNotExist:
        accounts = None

    if accounts:
    	# getting account information
        try:
            item = Items.objects.exclude(deleted = 1).get(id = item_id)
        except Items.DoesNotExist:
        	item = None

        context = {
            'accounts': accounts,
            'item': item
        }
        return render(request, 'fin/account.html', context)
    else:
        messages.warning(request, format('Invalid operation.'))
        return redirect('home')

# ------------------------------------------------------------------
# Transactions detail page for a specific account
# ------------------------------------------------------------------
@login_required()
def account_transactions(request, item_id, account_id):
	
    try:
        # TODO: Limit 60 days of transactions
        transactions = Item_account_transactions.objects.filter(item_accounts_id = account_id, item_accounts_id__items_id__user_id=request.user).exclude(item_accounts_id__items_id__deleted=1).order_by('-p_date')[:600]
    except Item_account_transactions.DoesNotExist:
        transactions = None

    if transactions:
    	# getting account information
        try:
            account_info = Item_accounts.objects.get(id = account_id)
        except Item_accounts.DoesNotExist:
        	account_info = None

        context = {
            'account': account_info,
            'transactions': transactions
        }
        return render(request, 'fin/transactions.html', context)
    else:
        messages.warning(request, format('Account refresh pending. Please check back again.'))
        url = '/details/' + str(item_id)
        return redirect(url)


# ------------------------------------------------------------------
# Remove item (TESTING ONLY)
# ------------------------------------------------------------------
@login_required()
def unlink_account(request, item_id):
	
	# Check if authorized to delete. Only members of cesr_team can delete accounts
	if not request.user.groups.filter(name='cesr_team').exists():
		messages.warning(request, format('Only staff can unlink accounts.'))
		return redirect('profile')
    
	try:
		# Checking if user deleting is the owner
		item = Items.objects.exclude(deleted = 1).get(id = item_id, user_id = request.user)
	except Items.DoesNotExist:
		item = None
        
	if not item:
		messages.warning(request, format('Cannot delete. Not the owner.'))
		return redirect('profile')
    	
	# Provide the access token for the Item you want to remove
	# TODO - this does not work!!!!!!!!!
	try:
		response = client.Item.remove(item.p_access_token)
	except plaid.errors.PlaidError as e:
		return JsonResponse(format_error(e))

	if response['removed'] == True:
		item.p_access_token = None # Setting access_token to null
		item.deleted = 1
		item.deleted_date = timezone.now()
		item.save(update_fields=['p_access_token','deleted','deleted_date'])
		# Updating actions table.
		new_action = User_Actions.objects.create(
			user_id = request.user,
			user_ip = request.META['REMOTE_ADDR'],
			action = "unlink_item",
			institution_id = item.p_institution_id,
			institution_name = item.p_item_name
		)
		logger.debug('REMOVE ITEM - User ' + str(request.user.id) + ' removed item id ' + str(item_id) + ' : ' + json.dumps(response))
	else:
		messages.warning(request, format('Something went wrong. Please report to help desk.'))
		return redirect('profile')
    
	# reset table 
	if not Items.objects.filter(user_id = request.user).exclude(deleted = 1).count():
		Users_With_Atleast_One_Linked_Institution.objects.filter(user_id = request.user).delete()

	messages.success(request, format(item.p_item_name + ' Removed.'))
	return redirect('profile')
    