# from betrics.user.model import authenticate_user
from aws_boto3_config import *

BOOK_LOGO = "https://bucket212121.s3.us-east-2.amazonaws.com/books_logo/"

table = get_table('book_subscription')
sport_books_table = get_table('sports_books')
book_subscribe_table = get_table("book_subscription")


def update_subscription(data):
    res = table.get_item(Key={
        'username': data.get('username')
    })

    sport_res = sport_books_table.get_item(Key={
        'id': data.get('id')
    })

    for k, v in sport_res.get('Item', {}).items():
        data[k] = v

    old_data = res.get("Item", {})

    list_of_book = old_data.get('book_list', [])

    flag = False
    indx = 0

    for idx, book in enumerate(list_of_book):
        if book.get('id') == data.get('id'):
            indx = idx
            flag = True
            break

    if len(list_of_book) != 0 and flag:
        del list_of_book[indx]

    list_of_book.append(data)

    old_data['book_list'] = list_of_book
    old_data['username'] = data.get('username')

    response = table.put_item(Item=old_data)
    return response


def calculate_avarage_rating(Items):
    books_rating = {}

    for item in Items:

        for book in item.get('book_list', []):

            if book.get('id') in books_rating and book.get("rating", "") != "":

                books_rating[book.get('id')].append(float(book.get('rating', 0)))

            elif book.get("rating", "") != "":

                books_rating[book.get('id')] = [float(book.get('rating', 0))]

                # return books_rating

    avg_book_rating = {k: round(sum(v) / len(v)) for k, v in books_rating.items()}

    return avg_book_rating


def update_data(data):
    res = table.get_item(Key={
        'username': data.get('username')
    })

    old_data = res.get("Item", {})
    old_book_list = old_data.get('book_list', [])

    new_item = True
    new_book_list = []
    for old_item in old_book_list:
        if old_item.get('id') == data.get('id'):
            new_item = False
            for att in data:
                if att != 'id':
                    old_item[att] = data.get(att, 'none')
        new_book_list.append(old_item)

    if new_item:
        sport_res = sport_books_table.get_item(Key={
            'id': data.get('id')
        })
        new_book_item = sport_res.get('Item')
        for att in data:
            if att != 'id':
                new_book_item[att] = data.get(att, 'none')
        new_book_list.append(new_book_item)

    db_item = {
        'username': data.get('username', 'error'),
        'book_list': new_book_list
    }
    response = table.put_item(Item=db_item)

    return response


def list_subscription(username):
    response = table.get_item(Key={'username': username})
    avg_res = book_subscribe_table.scan()

    book_data = avg_res.get("Items")
    average = calculate_avarage_rating(book_data)

    data = list(filter(lambda x: x.get('IsSubscribed') == True, response.get("Item").get('book_list')))

    updated_data = []

    for i in data:
        i.update({'bookBalance': str(i['bookBalance'])})
        updated_data.append(i)

        # Average rating logic removed by J.T. on 11/15/21
        '''
        if i.get('id') in average:
            i['rating'] = average[i.get('id')]
            i.update({'bookBalance' : str(i['bookBalance'])})
            updated_data.append(i)
        else:
            i['rating'] = 0
            i.update({'bookBalance' : str(i['bookBalance'])})
            updated_data.append(i)
        '''

    return sorted(updated_data, key=lambda x: (-float(x.get("rating", 0)), x.get("name")))
    # return data


def lambda_handler(events):
    http_method = events.get("http_method", "None")

    class User:
        email = "admin@admin.com"

    user = User()
    # user = authenticate_user(events.get('headers'))

    if http_method == "GET":
        response = list_subscription(user.email)

    elif http_method == "PUT":
        data = events.get("body")
        data['username'] = user.email
        # response = update_subscription(data)
        response = update_data(data)  # New function added by J.T. on 9/8/21

    elif http_method == "DELETE":
        pass

    return {
        "status": 200,
        "body": response
    }
