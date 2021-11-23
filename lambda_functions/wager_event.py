import json
import boto3
import copy
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from uuid import uuid1
import decimal
from pprint import pprint
from betrics.user.model import authenticate_user
import jwt
import bcrypt

# Added libraries - J.T. 8/8/21
from datetime import datetime
from pytz import timezone

db = boto3.resource('dynamodb')
client = boto3.client('lambda')


# Function to Set Up DynamoDB Table Resource
def get_table(table_name):
    return db.Table(table_name)


wager_table = get_table('wager_event')
bet_queue_table = get_table('bet_queue')
bet_tracking_table = get_table('bet_tracking')  # Added by J.T. on 8/8/21


def delete_temp_bet_queue(id):
    response = bet_queue_table.delete_item(
        Key={
            'id': id,
        },
    )


def event_data(id):
    response = bet_queue_table.get_item(Key={'id': id})
    return response.get('Item', {})


# Function to get time_stamp as string variable in EST
def get_current_time_est():
    timestamp_format = '%m-%d-%Y %H:%M:%S %z'
    now = datetime.now()
    now.replace(tzinfo=timezone('UTC'))
    now_est = now.astimezone(timezone('US/Eastern'))
    now_str = datetime.strftime(now_est, timestamp_format)
    return now_str


# Should not use "id" as a variable - it is already a reserved word in Python - J.T. 8/8/21
# def submit_wager_events(data):

#     data["bet_id"] =  str(uuid1())

#     parlay = []

#     teaser = []

#     for id in data['events']:

#         if data['bet_type'] == "straight":
#             queue_data = event_data(id)
#             # return queue_data
#             data[id] = queue_data

#         #Changed spelling from "parley" to "parlay" - J.T. on 8/8/21
#         elif data['bet_type'] == "parlay":
#             queue_data = event_data(id)
#             parlay.append(queue_data)

#         elif data['bet_type'] == "teaser":
#             queue_data = event_data(id)
#             teaser.append(queue_data)


#         delete_temp_bet_queue(id)


#     if len(teaser)!=0:
#         data['teaser'] = teaser

#     if len(parley)!= 0:
#         data['parlay'] = parlay


#     response = wager_table.put_item(
#         Item = data
#     )

#     return response


# Function to deduct wager amount from sports book balance
# Added by J.T. on 9/9/21
def update_book_balance(user, book, stake):
    book_table = get_table('book_subscription')
    response = book_table.get_item(Key={'username': user})

    old_data = response.get('Item')
    old_book_list = old_data.get('book_list', [])
    new_book_list = []

    for old_book in old_book_list:
        if old_book.get('id') == book:
            bet = float(stake)
            old_balance = float(old_book.get('bookBalance', '0.0'))
            new_balance = str(round(old_balance - bet, 2))
            old_book['bookBalance'] = new_balance
        new_book_list.append(old_book)

    db_item = {
        'username': user,
        'book_list': new_book_list
    }
    book_table.put_item(Item=db_item)

    return [stake, old_balance, new_balance]


# Function Created by J.T. on 8/8/21
# Function used to post wager data to bet_tracking table
def submit_wager(wager_data, event_list):
    wager_data.update({
        'id': str(uuid1()),
        'status': 'pending',
        "time_stamp": get_current_time_est(),
        'events': event_list
    })

    bet_amount = wager_data.get('at_risk', False)
    book_id = wager_data.get('book_id', False)
    user_id = wager_data.get('username', False)
    print([bet_amount, book_id, user_id])
    if bet_amount and book_id and user_id:
        response = update_book_balance(user_id, book_id, bet_amount)
        print(response)

    bet_tracking_table.put_item(Item=json.loads(json.dumps(wager_data), parse_float=Decimal))


# Function Created by J.T. on 8/8/21
# Function used to post individual events to wager_events table and delete from bet_queue table
# Expects 'data' input to be a list of events passed from the front end in the same schema as found in the bet queue table

def check_rated_book_balance(user, book_id, balance):
    book_table = get_table('book_subscription')
    response = book_table.get_item(Key={'username': user})

    # result = list(filter(lambda x: x['rated'] == True and x['id'] == book_id and float(x['bookBalance']) < float(balance) ,response.get('Item',{}).get('book_list' ,[])))
    result = list(filter(
        lambda x: x.get('rated') == True and x.get('id') == book_id and float(x.get('bookBalance', 0.0)) < float(
            balance), response.get('Item', {}).get('book_list', [])))

    if len(result) > 0:

        return True

    else:
        return False


def create_wager_events(data, user):
    events_list = []

    for event_data in data:

        if check_rated_book_balance(user.email, event_data['sr:book:id'], event_data['bet_amount']):
            return {"status": 400}

    for event_data in data:

        if 'id' in event_data:
            bet_id = event_data['id']
            del event_data['id']
            events_list.append(bet_id)
        else:
            bet_id = False

        # Add status and time_stamp variable to event_data
        if bet_id:
            event_data['bet_id'] = bet_id
            event_data['status'] = 'pending'
            event_data['username'] = user.email
            event_data['time_stamp'] = get_current_time_est()

            # Post event to wager_events table and delete event from queue

            response = wager_table.put_item(Item=json.loads(json.dumps(event_data), parse_float=Decimal))
            delete_temp_bet_queue(
                bet_id)  # Commented this for now for testing purposes, but when ready we should delete the event from the queue table after it's posted to wager_events

    return events_list


def lambda_handler(events):
    http_method = events.get('http_method', 'None')

    user = events.get("user")

    if http_method == "POST":
        if events.get('body').get('bubble', False):
            body = events.get('body')

            if body.get('wager_data', False):
                response = create_wager_events(body['wager_data'], user)

            elif body.get('wager_info', False) and body.get('wager_list', False):
                body['wager_info'].update({'username': user.email})
                submit_wager(body['wager_info'], body['wager_list'])
                response = body['wager_list']

            else:
                response = 'Body missing wager_data or wager_info...'
        else:

            data = events.get('body').get("wager_data")
            events['body']['wager_info']['username'] = user.email
            # response = submit_wager_events(data)

            response = create_wager_events(data, user)

            if not isinstance(response, list) and response.get('status') == 400:
                return response

            submit_wager(events.get('body').get('wager_info'), response)

    return {
        "status": 200,
        "body": response
    }
