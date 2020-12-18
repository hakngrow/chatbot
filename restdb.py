import random
import requests
import json

FIELD_ACCOUNT_ID = 'account_id'
FIELD_USER_ID = 'user_id'
FIELD_PASSWORD = 'password'
FIELD_NAME = 'name'
FIELD_DATE_OF_BIRTH = 'date_of_birth'
FIELD_ADDRESS = 'address'
FIELD_ORDER_LIMIT = 'order_limit'

FIELD_TYPE = 'type'
FIELD_SYMBOL = 'symbol'
FIELD_SHARES = 'shares'
FIELD_PRICE = 'price'

COL_ACCOUNTS = 'accounts'
COL_ORDERS = 'orders'

DB_URL = 'https://chatbot-fb42.restdb.io/rest/'

DB_HEADERS = {
  'content-type': 'application/json',
  'x-apikey': '3390f696777fffc8e818fdca75f1207198019',
  'cache-control': 'no-cache'
}

ACC_CHALLENGE_FIELDS = [FIELD_PASSWORD]

ACC_CHALLENGE_FIELD_COUNT = 1

def get_challenge_fields():

  fields = random.sample(ACC_CHALLENGE_FIELDS, ACC_CHALLENGE_FIELD_COUNT)

  return fields


def get_account(account_id):

  url = DB_URL + COL_ACCOUNTS + '?q={"' + FIELD_ACCOUNT_ID + '": "' + account_id + '"}'

  response = requests.request("GET", url, headers=DB_HEADERS)

  return response


def create_order(account_id, order_type, symbol, shares, price):

  url = DB_URL + COL_ORDERS

  dict_order = {
    FIELD_ACCOUNT_ID: account_id,
    FIELD_TYPE: order_type,
    FIELD_SYMBOL: symbol,
    FIELD_SHARES: shares,
    FIELD_PRICE: price
  }

  print(dict_order)

  json_order = json.dumps(dict_order)

  response = requests.request("POST", url, data=json_order, headers=DB_HEADERS)

  print(response.text)
