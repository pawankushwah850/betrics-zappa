from marshmallow import Schema, fields
import datetime
import boto3
import copy


def get_database():
    return boto3.resource('dynamodb')


def get_table(table_name):
    database = get_database()
    return database.Table(table_name)


class SportBookSchema(Schema):
    bookId = fields.String()
    bookName = fields.String()
    createdBy = fields.String()
    createdDate = fields.DateTime(default=datetime.datetime.now())


class SportBook:

    def __init__(self, username):
        self.table = get_table(table_name="sports_books")
        self._book_subscribe_table = get_table(table_name="book_subscription")
        self.book_ids = {}
        self.username = username

    def calculate_avarage_rating(self, Items):

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

    def get_list(self):
        response = self.table.scan()
        res = self._book_subscribe_table.get_item(Key={
            "username": self.username
        })

        avg_res = self._book_subscribe_table.scan()

        for i in res.get('Item', {}).get('book_list', []):

            if i.get('IsSubscribed'):
                self.book_ids[i.get('id')] = i.get('IsSubscribed')

        data = list(filter(lambda x: not x.get('id') in self.book_ids, response.get('Items')))
        print(self.book_ids)
        print(data)

        book_data = avg_res.get("Items")
        # average = self.calculate_avarage_rating(book_data)
        # print(average)

        # return average

        updated_data = []
        for i in data:
            updated_data.append(i)
            # Average rating logic removed by J.T. on 11/15/21
            '''
            if i.get('id') in average:
                i['rating'] = average[i.get('id')]
                updated_data.append(i)
            else:
                i['rating'] = 0
                updated_data.append(i)
            '''

        # return updated_data
        return sorted(updated_data, key=lambda x: (-x["rating"], x["name"]))

    def get_all_books(self):
        response = self.table.scan()
        all_books = response.get('Items', [])

        response = self._book_subscribe_table.get_item(Key={
            "username": self.username
        })
        user_books = response.get('Item').get('book_list', [])

        new_list = []
        for book in all_books:
            new_item = copy.deepcopy(book)
            for user_book in user_books:

                if book['id'] == user_book['id']:
                    new_item.update({
                        'bookBalance': str(user_book.get('bookBalance', '0.0')),
                        'rating': user_book.get('rating', 0),
                        'IsSubscribed': user_book.get('IsSubscribed', False)
                    })

            if 'bookBalance' not in new_item:
                new_item.update({'bookBalance': '0.0'})
            if 'rating' not in new_item:
                new_item.update({'rating': 0})
            if 'IsSubscribed' not in new_item:
                new_item.update({'IsSubscribed': False})

            new_list.append(new_item)

        subscribe = list(filter(lambda x: x['IsSubscribed'] == True, new_list))
        unsubscribe = list(filter(lambda x: x['IsSubscribed'] == False, new_list))

        subscribe.sort(key=lambda x: (-x['rating'], x['name']))
        unsubscribe.sort(key=lambda x: (-x['rating'], x['name']))

        return subscribe + unsubscribe


def lambda_handler(event):
    user = event.get("user")
    obj = SportBook(user.email)

    # response  = obj.get_list()

    # Function added by J.T. on 9/4/21
    response = obj.get_all_books()

    return {
        "status": 200,
        "body": response
    }
