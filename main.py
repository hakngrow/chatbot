import pandas as pd
import pprint

import requests 

from datetime import datetime

from flask import Flask, request

import yahoo_fin.stock_info as si

import config as CFG
import alphavantage as AV
import restdb as RDB


app = Flask(__name__)

@app.route('/') # this is the home page route
def hello_world():
    return "Hello world!"

def get_fulfillment_messages(messages):

  fulfillment_msgs = []

  for message in messages:
    fulfillment_msgs.append({CFG.JTAG_TEXT: {CFG.JTAG_TEXT: [message]}})

  return fulfillment_msgs


def get_symbols(index):

  symbols = []

  if index == CFG.INDEX_DOW:
    symbols = si.tickers_dow()
  elif index == CFG.INDEX_NASDAQ:
    symbols = si.tickers_nasdaq()
  elif index == CFG.INDEX_SP500:
    symbols = si.tickers_sp500()

  return {
    'fulfillmentText': str(symbols),
    'displayText': '25',
    'source': 'webhookdata',
    'platform': 'FACEBOOK',
  }

def get_live_price(symbol):

  price = si.get_live_price(symbol)

  return {
    'fulfillmentText': 'US$' + f'{price:7.2f}',
    'displayText': '25',
    'source': 'webhookdata',
    'platform': 'FACEBOOK',
  }

def get_asset_info(symbol, attributes):

  url = AV.get_asset_info_url(symbol, attributes)

  response = requests.get(url).json()

  lst_messages = []

  for attribute in attributes:

    value = response[attribute]

    message = attribute + ': ' + value

    if value != CFG.ATTR_VAL_NONE:
      if attribute == CFG.ATTR_EBITDA or \
        attribute == CFG.ATTR_MKT_CAP or \
        attribute == CFG.ATTR_SHARES_FLOAT:

        message = attribute + ': ' + f'{int(value):,d}'

    lst_messages.append(message)

  return {
    "fulfillmentMessages": get_fulfillment_messages(lst_messages),
    'source': 'webhookdata',
    'platform': 'FACEBOOK'
  }


def get_account(account_id):

  response = RDB.get_account(account_id).json()

  account = None

  # Account info NOT found
  if len(response) != 0:
    account = response[0]

  return account;


def get_challenge_text(fields):

  challenge_text = 'To verify your identity, I need you to provide me your '

  field_count = len(fields)

  if field_count == 1:

    challenge_text = challenge_text + fields[0]

  else:

    for i in range(field_count - 1):
      challenge_text = challenge_text + fields[i] + ', '

    challenge_text = challenge_text[:-1] + ' and ' + fields[len(fields) - 1]

  return challenge_text + '.'


def challenge_user(account_id):

  account = get_account(account_id)

  fulfillment_text = f'The account ID {account_id} is invalid. Please try again.'

  if account is not None:

    fields = RDB.get_challenge_fields()

    fulfillment_text = get_challenge_text(fields)

  return {
    'fulfillmentText': fulfillment_text,
    'source': 'webhookdata',
    'platform': 'FACEBOOK'
  }

def verify_password(account_id, password, session_id, session_parameters):

  account = get_account(account_id)

  fulfillment_text = 'The password you have provided is invalid. Please try again.'

  session_updates = {
    CFG.JTAG_NAME: session_id + '/contexts/' + CFG.CTX_SESSION
  }

  if account.get(RDB.FIELD_PASSWORD) == password:

    fulfillment_text = 'Your login is successful!'

    session_updates[CFG.PARAM_LOGIN] = CFG.PARAM_LOGIN_VAL_OK

  else:

    session_updates[CFG.PARAM_LOGIN] = CFG.PARAM_LOGIN_VAL_FAILED

    attempts = session_parameters.get(CFG.PARAM_LOGIN_ATTEMPTS)

    if attempts is None:
      session_updates[CFG.PARAM_LOGIN_ATTEMPTS] = 1
    else:
      session_updates[CFG.PARAM_LOGIN_ATTEMPTS] = attempts + 1

  return {
    'fulfillmentText': fulfillment_text,
    'source': 'webhookdata',
    'platform': 'FACEBOOK',
    CFG.JTAG_OUTPUT_CONTEXTS: [ session_updates]
  }


def create_order(order_type, symbol, shares, price, session_parameters):

  status = session_parameters.get(CFG.PARAM_LOGIN_STATUS)

  fulfillment_text = 'You have to login before you can create a trade order.'

  if status != CFG.PARAM_LOGIN_STATUS_VAL_FAILED:

    account_id = session_parameters.get(CFG.PARAM_ACC_ID)

    RDB.create_order(account_id, order_type, symbol, shares, price)

    fulfillment_text = f'Your order to {order_type} {shares} shares of {symbol} at ${price} is created.'

  return {
    'fulfillmentText': fulfillment_text,
    'source': 'webhookdata',
    'platform': 'FACEBOOK'
  }



def get_session_parameters(contexts):

  parameters = None

  for context in contexts:
    if context.get(CFG.JTAG_NAME).endswith(CFG.CTX_SESSION):
      parameters = context.get(CFG.JTAG_PARAMETERS)

  return parameters


def do_action(action, session_id, parameters, contexts):

  action_result = {
    "fulfillmentText": 'The intent action detected was ' + action + ' @ ' + str(datetime.now()),
    "displayText": '25',
    "source": "webhookdata"
  }

  if action == CFG.ACT_CHALLENGE_USER:

    account_id = parameters.get(CFG.PARAM_ACC_ID)

    action_result = challenge_user(account_id)  

  elif action == CFG.ACT_VERIFY_PWD:

    session_parameters = get_session_parameters(contexts)

    account_id = session_parameters.get(CFG.PARAM_ACC_ID)
    password = parameters.get(CFG.PARAM_PASSWORD)

    action_result = verify_password(account_id, password, session_id, session_parameters)

  elif action == CFG.ACT_GET_SYMBOLS:

    index = parameters.get(CFG.PARAM_INDEX)

    action_result = get_symbols(index)

  elif action == CFG.ACT_GET_LIVE_PRICE:

    symbol = parameters.get(CFG.PARAM_SYMBOL)

    action_result = get_live_price(symbol)

  elif action == CFG.ACT_GET_ASSET_INFO:

    symbol = parameters.get(CFG.PARAM_SYMBOL)
    attributes = parameters.get(CFG.PARAM_ASSET_ATTRIBUTE)

    action_result = get_asset_info(symbol, attributes)

  elif action == CFG.ACT_GET_ACC_INFO:

    account_id = parameters.get(CFG.PARAM_ACC_ID)

    action_result = get_account(account_id)

  elif action == CFG.ACT_ORDER_CREATE:

    order_type = parameters.get(CFG.PARAM_ORDER_TYPE)
    symbol = parameters.get(CFG.PARAM_SYMBOL)
    shares = parameters.get(CFG.PARAM_SHARES)
    price = parameters.get(CFG.PARAM_PRICE)

    create_order(order_type, symbol, shares, price, get_session_parameters(contexts))

  return action_result

    
@app.route('/webhook', methods=['POST'])
def webhook():
  
  req = request.get_json(silent=True, force=True)
  
  session_id = req.get(CFG.JTAG_SESSION)

  query_result = req.get(CFG.JTAG_QUERY_RESULT)

  action = query_result.get(CFG.JTAG_ACTION)

  parameters = query_result.get(CFG.JTAG_PARAMETERS)

  contexts = query_result.get(CFG.JTAG_OUTPUT_CONTEXTS)

  action_result = do_action(action, session_id, parameters, contexts)

  return action_result

@app.route('/y') 
def yahoo_finance():

  #dict_info = si.get_analysts_info('nflx')

  #df_info = pd.DataFrame.from_dict(dict_info, orient='index')

  #pprint.pprint(dict_info)

  symbols = si.tickers_dow()

  return str(symbols)
  #return "yahoo! " + str(datetime.now())
    
   
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080) # This line is required to run Flask on repl.it