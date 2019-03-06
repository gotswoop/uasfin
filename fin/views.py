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
from .models import Items, Item_accounts, Item_account_transactions
from django.conf import settings
from django.contrib import messages
import logging
from django.core import serializers

access_token = None
client = plaid.Client(client_id=settings.PLAID_CLIENT_ID, secret=settings.PLAID_SECRET, public_key=settings.PLAID_PUBLIC_KEY, environment=settings.PLAID_ENV, api_version='2018-05-22')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# SITE HOME. This is the dashboard
# ------------------------------------------------------------------
@login_required()
def home(request):

  try:
    items = Items.objects.filter(user_id = request.user).order_by('p_item_name')
  except Items.DoesNotExist:
  	items = None

  # Configuring the webhook here..
  webhook_url = 'https://' + request.get_host() + '/' + settings.PLAID_WEBHOOK_URL
  
  context = {
	    'title': "Dashboard",
        'items': items,
        'plaid_public_key': settings.PLAID_PUBLIC_KEY,
		'plaid_environment': settings.PLAID_ENV,
		'plaid_products': settings.PLAID_PRODUCTS,
		'plaid_webhook_url': webhook_url
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
# GET ACCESS TOKEN
# ------------------------------------------------------------------
@require_http_methods(["POST"])
def get_access_token(request):
  
  global access_token  ## TODO: YIKES
  public_token = request.POST.get('public_token', '')
  
  try:
    exchange_response = client.Item.public_token.exchange(public_token)
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
  	return JsonResponse({'error': None, 'auth': exchange_response, 'item': item_response['item'], 'institution': institution_response['institution'], 'duplicate': 1})
  else:
  	# Add record
    new_item = Items.objects.create(
	       user_id = request.user, 
	       p_access_token = access_token, 
	       p_item_id = exchange_response['item_id'], 
	       p_institution_id = item_response['item']['institution_id'], 
	       p_item_name = institution_response['institution']['name'],
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
  return JsonResponse({'error': None, 'auth': exchange_response, 'item': item_response['item'], 'institution': institution_response['institution'], 'duplicate': 0})
								

# ------------------------------------------------------------------
# DEBUG: PRETTY PRINT RESPONSE
# ------------------------------------------------------------------
def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True))

# ------------------------------------------------------------------
# WEBHOOK - Incoming connection
# ------------------------------------------------------------------
# TODO: restrict access to specific subnets
@require_http_methods(["POST"])
@csrf_exempt
def webhook(request):
    incoming = {}
    incoming = json.loads(request.body.decode('UTF-8')) # decode needed for python < 3.6
    #for key, value in incoming.items():
    #       temp = '\t' + str(key) + ": " + str(value) + '\n'
    #       out +=temp
    logger.debug('Incoming payload from Plaid: ' + json.dumps(incoming)) 
    # Check other webhook_types and only if ERROR is NONE
    if incoming['webhook_type'] == "TRANSACTIONS":
        if incoming['webhook_code'] in ["INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"]:
            logger.debug('Getting transactions for item_id = ' + incoming['item_id'])
            get_transactions(incoming['item_id'])
        elif incoming['webhook_code'] == "TRANSACTIONS_REMOVED":                
            # remove_transactions()
            logger.debug('Rare remove transactions for item_id = ' + incoming['item_id'])
        else:
        	logger.debug('*** Should not be in here. item_id = ' + incoming['item_id'])
    return HttpResponse("")

# ------------------------------------------------------------------
# Get Transactions for an item
# ------------------------------------------------------------------
def get_transactions(item_id):
  # Pull transactions for the last 1095 days (3 years)
  try:
    res = Items.objects.values('p_access_token').get(p_item_id = item_id)
  except Items.DoesNotExist:
    logger.debug('### No corresponding entry for ' + item_id + ' in fin_items table')
    res = None

  if res == None:
    logger.debug('### ARGH: Still getting records for old sandboxes and deployments')
    return ""

  access_token = res['p_access_token']
  start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-730))
  end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
  try:
    transactions_response = client.Transactions.get(access_token, start_date, end_date)
  except plaid.errors.PlaidError as e:
    return jsonify(format_error(e))
  
  #pretty_print_response(transactions_response)
  for transaction in transactions_response['transactions']:
    account_id = transaction['account_id']
    item_account_obj = Item_accounts.objects.get(p_account_id = account_id)
    if item_account_obj:
        try:
            already_exists = Item_account_transactions.objects.get(p_transaction_id = transaction['transaction_id'], item_accounts_id = item_account_obj)
        except Item_account_transactions.DoesNotExist:
            already_exists = None

        if already_exists:
        	# Skip to next transaction
        	continue

        new_transaction = Item_account_transactions.objects.create(
           item_accounts_id = item_account_obj,
           p_account_id = transaction['account_id'],
           p_account_owner = transaction['account_owner'],
           p_amount = transaction['amount'],
           p_category = json.dumps(transaction['category']),
           p_category_id = transaction['category_id'],
           p_date = transaction['date'],
           p_iso_currency_code = transaction['iso_currency_code'],
           p_location_address = transaction['location']['address'],
           p_location_city = transaction['location']['city'],
           p_location_lat = transaction['location']['lat'],
           p_location_lon = transaction['location']['lon'],
           p_location_state = transaction['location']['state'],
           p_location_store_number = transaction['location']['store_number'],
           p_location_zip = transaction['location']['zip'],
           p_name = transaction['name'],
           p_payment_meta_by_order_of = transaction['payment_meta']['by_order_of'],
           p_payment_meta_payee = transaction['payment_meta']['payee'],
           p_payment_meta_payer = transaction['payment_meta']['payer'],
           p_payment_meta_payment_method = transaction['payment_meta']['payment_method'],
           p_payment_meta_payment_processor = transaction['payment_meta']['payment_processor'],
           p_payment_meta_ppd_id = transaction['payment_meta']['ppd_id'],
           p_payment_meta_reason = transaction['payment_meta']['reason'],
           p_payment_meta_reference_number = transaction['payment_meta']['reference_number'],
           p_pending = transaction['pending'],
           p_pending_transaction_id = transaction['pending_transaction_id'],
           p_transaction_id = transaction['transaction_id'],
           p_transaction_type = transaction['transaction_type'],
           p_unofficial_currency_code = transaction['unofficial_currency_code']
        )
        # logger.debug('TRANSACTIONS ADDED: ' + serializers.serialize('json', [new_transaction]))
        logger.debug('TRANSACTIONS ADDED: ' + new_transaction.p_transaction_id)
    else:
        logger.debug('ERROR: Cannot find the account that we are trying to add or update transactions into')

  return ""
  
# ------------------------------------------------------------------
# Account details view for a specific item id
# ------------------------------------------------------------------
@login_required()
def account_details(request, item_id):
	
    try:
        # TODO: Limit 60 days of transactions
        accounts = Item_accounts.objects.filter(items_id = item_id).filter(items_id__user_id=request.user).order_by('p_account_name')
    except Item_accounts.DoesNotExist:
        accounts = None

    if accounts:
    	# getting account information
        try:
            item = Items.objects.get(id = item_id)
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
        transactions = Item_account_transactions.objects.filter(item_accounts_id = account_id).filter(item_accounts_id__items_id__user_id=request.user).order_by('-p_date')[:600]
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
def remove_item(request, item_id):
	
    try:
        item = Items.objects.get(id = item_id, user_id = request.user)
    except Items.DoesNotExist:
        item = None

    if item:
    	# Provide the access token for the Item you want to remove
    	# TODO - this does not work!!!!!!!!!
        try:
            response = client.Item.remove(item.p_access_token)
        except plaid.errors.PlaidError as e:
            return JsonResponse(format_error(e))

        if response['removed'] == True:
        	item.delete()
        	logger.debug('REMOVE ITEM - User ' + str(request.user.id) + ' removed item id ' + str(item_id) + ' : ' + json.dumps(response))
        else:
            messages.warning(request, format('Something went wrong. Please report to help desk.'))
            return redirect('profile')
        
        messages.success(request, format(item.p_item_name + ' Removed.'))
        return redirect('profile')
    else:
        messages.warning(request, format('Invalid Operation.'))
        return redirect('profile')

# ------------------------------------------------------------------
# Remove item (TESTING ONLY)
# ------------------------------------------------------------------
def format_error(e):
  return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }
