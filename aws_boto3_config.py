from boto3 import resource

get_resource = lambda x: resource('dynamodb', region_name='us-east-2')
get_table = lambda x: get_resource(None).Table(x)

table = get_table('book_subscription')
