#import base64
#import os
import datetime
import plaid
import json
#import time
from pprint import pprint

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

access_token = None
client = plaid.Client(client_id=settings.PLAID_CLIENT_ID, secret=settings.PLAID_SECRET, public_key=settings.PLAID_PUBLIC_KEY, environment=settings.PLAID_ENV, api_version='2018-05-22')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# SITE HOME. This is the dashboard
# ------------------------------------------------------------------
@login_required()
def home(request):
  try:
    user_institutions = Items.objects.filter(user_id = request.user).order_by('p_item_name')
  except Items.DoesNotExist:
  	user_institutions = None

  if user_institutions:
    accounts = {}
    for inst in user_institutions:
      temps = Item_accounts.objects.filter(items_id = inst).order_by('p_account_name')
      a = []
      for temp in temps:
        x_temp = {'fin_account_id': temp.id, 'fin_account_name': temp.p_account_name, "fin_account_official_name": temp.p_account_official_name, "fin_account_subtype": temp.p_account_subtype, "fin_account_balance": temp.p_account_balance_current}
        a.append(x_temp)
      accounts[inst.p_item_name] = a
  else:
    accounts = None
  
  # Configuring the webhook here..
  webhook_url = 'https://' + request.get_host() + '/' + settings.PLAID_WEBHOOK_URL
  
  # logger.debug(webhook_url)
  context = {
	    'title': "Dashboard",
        'accounts': accounts,
        'plaid_public_key': settings.PLAID_PUBLIC_KEY,
		'plaid_environment': settings.PLAID_ENV,
		'plaid_products': settings.PLAID_PRODUCTS,
		'plaid_webhook_url': webhook_url
  }
  if accounts:
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
  print("PUBLIC_TOKEN", public_token)
 
  try:
    exchange_response = client.Item.public_token.exchange(public_token)
  except plaid.errors.PlaidError as e:
    return JsonResponse(format_error(e))

  access_token = exchange_response['access_token'] 
  logger.debug("Item Added (access token): " + access_token) ## TODO: Debug
  pretty_print_response(exchange_response)

  # Get item info using token
  item_response = client.Item.get(access_token)
  pretty_print_response(item_response)

  # Get more item info using item institution id
  institution_response = client.Institutions.get_by_id(item_response['item']['institution_id'])
  pretty_print_response(institution_response)

  try:
    already_exists = Items.objects.get(user_id = request.user, p_institution_id = item_response['item']['institution_id'])
  except Items.DoesNotExist:
  	already_exists = None

  if already_exists:
  	# Return to dashboard if it's a duplicate
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

  # Get item_accounts and insert into database.
  try:
    accounts_response = client.Accounts.get(access_token)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  
  pretty_print_response(accounts_response)

  if accounts_response:
    if accounts_response['item']['error'] is not None:
        print("YIKES")
    else:
        accounts = accounts_response['accounts']
        for account in accounts:
            Item_accounts.objects.create(
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
@require_http_methods(["POST"])
@csrf_exempt
def webhook(request):
    out = 'Incoming payload from Plaid...\n'
    incoming = {}
    incoming = json.loads(request.body.decode('UTF-8')) # decode needed for python < 3.6
    for key, value in incoming.items():
        temp = '\t' + str(key) + ": " + str(value) + '\n'
        out +=temp
    logger.debug(out)
    # Check other webhook_types and only if ERROR is NONE
    if incoming['webhook_type'] == "TRANSACTIONS":
        if incoming['webhook_code'] in ["INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"]:
            get_transactions(incoming['item_id'])
        elif incoming['webhook_code'] == "TRANSACTIONS_REMOVED":
            # remove_transactions()
            print("# Rare remove transaction event")
        else:
        	print("# 11234: SHOULD NOT BE IN HERE!!!!!")
    return HttpResponse("")

# ------------------------------------------------------------------
# Get Transactions for an item
# ------------------------------------------------------------------
def get_transactions(item_id):
  # Pull transactions for the last 1095 days (3 years)
  logger.debug(item_id)
  try:
    res = Items.objects.values('p_access_token').get(p_item_id = item_id)
  except Items.DoesNotExist:
    res = None

  if res == None:
    logger.debug("### HAHA: Still getting records for old shit")
    return ""

  access_token = res['p_access_token']
  start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-600))
  end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
  try:
    transactions_response = client.Transactions.get(access_token, start_date, end_date)
  except plaid.errors.PlaidError as e:
    return jsonify(format_error(e))
  
  # pretty_print_response(transactions_response)
  for transaction in transactions_response['transactions']:
    account_id = transaction['account_id']
    item_account_obj = Item_accounts.objects.get(p_account_id = account_id)
    if item_account_obj:

        try:
            already_exists = Item_account_transactions.objects.get(p_transaction_id = transaction['transaction_id'], item_accounts_id = item_account_obj.id)
        except Item_account_transactions.DoesNotExist:
            already_exists = None

        if already_exists:
        	# TODO: Update it?
        	return ""

        Item_account_transactions.objects.create(
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
    else:
        print("### THIS WAS NEVER SUPPOSED TO HAPPEN")

  return ""
  
# ------------------------------------------------------------------
# Account details view
# ------------------------------------------------------------------
def account_details(request, account_id):
	
    try:
        transactions = Item_account_transactions.objects.filter(item_accounts_id = account_id).order_by('-p_date')[:20]
        # TODO: Limit 60 days of transactions
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
        return redirect('home')

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

        pretty_print_response(response)
        if response['removed'] == True:
        	item.delete()
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
