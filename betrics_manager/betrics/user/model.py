from uuid import uuid4

import bcrypt
from dynamorm import DynaModel, GlobalIndex, ProjectAll
from marshmallow import fields
import jwt
secret = 'YvihUD3bFcl89d5tOdi2QjHyQekt2opsIrzygyNhhG34hkR6sICwx7c5i1k8INCu92l2pH5HX1eQO9nrfmco'

# In this example we'll use Marshmallow, but you can also use Schematics too!
# You can see that you have to import the schema library yourself, it is not abstracted at all

class Password(fields.Field):
    """Field that serializes to a string of numbers and deserializes
    to a list of numbers.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        return bcrypt.hashpw(value, bcrypt.gensalt())


class User(DynaModel):
    class Table:
        name = 'user'
        hash_key = 'id'
        read = 25
        write = 5

    class ByEmail(GlobalIndex):
        name = 'by-email'
        hash_key = 'email'
        read = 25
        write = 5
        projection = ProjectAll()

    class Schema:
        id = fields.UUID(default=str(uuid4()))
        first_name = fields.String()
        last_name = fields.String()
        email = fields.Email()
        password = Password()
        created_at = fields.DateTime()
        is_active = fields.Boolean(default=True)
        active_contest = fields.List(fields.String())
        aws_sports_books = fields.List(fields.String())
        bank_roll_reserve = fields.Integer(default=int(0))
        bettor_level = fields.String(default=None)
        contest_entry = fields.List(fields.String(), default=[])
        default_sportbook = fields.String(default=None)
        default_bb_wager_type = fields.String(default=None)
        default_bb_wager_value = fields.Integer()
        default_bb_real_type = fields.String()
        default_bb_real_value = fields.Integer()
        engines = fields.List(fields.String())
        my_betrics = fields.List(fields.String())
        my_sports_book = fields.List(fields.String())
        nick_name = fields.String()
        role = fields.String()# admin, public_user, free and paid

    def check_password(self, plain_password):
        return bcrypt.checkpw(plain_password, self.password)

    def __dict__(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
        }


class ForgotPasswordToken(DynaModel):
    class Table:
        name = 'forget_password_token'
        hash_key = 'user_id'
        read = 25
        write = 5

    class Schema:
        user_id = fields.UUID(default=str(uuid4()))
        token = fields.String()



class HTTPException(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code

def authenticate_user(headers):
    if not headers.get('Authorization'):
        raise HTTPException('Auth header not provided', 401)
    try:
        data = jwt.decode(headers.get('Authorization'), secret, algorithms=["HS256"])
    except Exception as e:
        print(e)
        raise HTTPException('Invalid auth token.', 401)

    user = User.get(id=data.get('user_id'))
    if not user:
        raise HTTPException('Invalid auth token.', 401)
    return user

# print(authenticate_user({"Authorization":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMjMzNzVhMmMtZTgyZi00OGIyLTg2YzItOTI3Y2ZkMDQ1ZDM3In0.87eSaRIrdJf-mXRD23H-J4q34Yzdf1UzTemuCgExHqQ"}).email)
# authenticate_user({'Authorization':'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiOTRiZDNhMGUtZTRiYi00YTliLTk0OGItOWM5ZjYxMDVlMjY0In0.KAIlpEAOmGu9MT7YqQ6YUeMyFyBsw8VmyhmZakzitPA'})
# {'user_id': '94bd3a0e-e4bb-4a9b-948b-9c9f6105e264'}