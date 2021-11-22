from betrics.user.model import User, authenticate_user
import json
import boto3
import base64
import datetime
import botocore

s3 = boto3.client('s3')
db = boto3.resource('dynamodb')

s3_bucket = boto3.resource('s3')

secret = 'YvihUD3bFcl89d5tOdi2QjHyQekt2opsIrzygyNhhG34hkR6sICwx7c5i1k8INCu92l2pH5HX1eQO9nrfmco'

AVATAR = "https://betrics-profile-picture.s3.us-east-2.amazonaws.com/"


def db_table(table_name):
    return db.Table(table_name)


class HTTPException(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


data_customer = db_table('stripe_customer')


def get_user(user):
    user_data = user.__dict__()

    try:
        name = str(user.id) + '.jpg'
        s3_bucket.Object('betrics-profile-picture', name).load()
        user_data['avatar'] = AVATAR + name

    except botocore.exceptions.ClientError as e:
        user_data['avatar'] = None

    return user_data


# automatic rated book subscrption function

def auto_rated_book_subscription(data):
    table = db_table('sports_books')
    subscription_table = db_table('book_subscription')

    res = subscription_table.get_item(Key={
        'username': data.get('email')
    })

    res = table.scan()
    rated_book = list(filter(lambda x: x.get('rated') == True, res.get('Items')))

    old_data = res.get("Item", {})
    list_of_book = old_data.get('book_list', [])

    for r_book in rated_book:
        r_book["IsSubscribed"] = True
        r_book["subscribedDate"] = str(datetime.datetime.now())
        r_book["bookBalance"] = '10000'
        list_of_book.append(r_book)

    old_data['book_list'] = list_of_book
    old_data['username'] = data.get('email')

    response = subscription_table.put_item(Item=old_data)


def create_user(data):
    users_with_same_email = User.scan(email=data['email'].lower())
    auto_rated_book_subscription(data)
    # data['stripe_customer_id'] = payment_sheet()

    if not list(users_with_same_email):
        return User.put_unique(data)

    raise HTTPException("User with the email already exists", 400)


def update_user(user, data):
    if user:

        image = data.get('avatar', False)

        if image:
            name = str(user.id) + '.jpg'
            image = image[image.find(",") + 1:]
            dec = base64.b64decode(image + "===")
            s3.put_object(Bucket='betrics-profile-picture', Key=name, Body=dec, ContentType="image/png")

        for key, value in data.items():
            user.__setattr__(key, value)
        user.save()

        return user.__dict__()


def delete_user(user):
    user.delete()
    return True


def lambda_handler(event):
    http_method = event['http_method']

    try:
        if not http_method == 'POST':
            user = authenticate_user(event.get('headers'))
            if http_method == 'GET':
                res_data = get_user(user)
            elif http_method == 'PUT':
                res_data = update_user(user, event['body'])
            elif http_method == 'DELETE':
                res_data = delete_user(user)
        else:
            res_data = create_user(event['body'])
        return {
            'statusCode': 200,
            'body': res_data
        }
    except HTTPException as e:
        return {
            'statusCode': e.status_code,
            'error': str(e),
            "event": event
        }
