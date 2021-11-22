import json
import boto3
from betrics.user.model import User
from dynamorm.exceptions import HashKeyExists
import jwt

secret = 'YvihUD3bFcl89d5tOdi2QjHyQekt2opsIrzygyNhhG34hkR6sICwx7c5i1k8INCu92l2pH5HX1eQO9nrfmco'


def get_user_with_from_email(email):
    users_with_same_email = list(User.scan(email=email))
    return users_with_same_email[0] if users_with_same_email else None


def authenticate_user(email, password):
    user = get_user_with_from_email(email)
    if user and user.check_password(password):
        return user
    else:
        return 'Invalid Email id or password.'


class HTTPException(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


def login_user(email="admin@admin.com", password="12345"):
    user = authenticate_user(email, password)
    if isinstance(user, User):
        return jwt.encode({"user_id": str(user.id)}, secret, algorithm="HS256")
    raise HTTPException(user, 401)

def lambda_handler(data):

    print(data)
    token = login_user(data.get("email"), data.get("password"))
    # TODO implement
    return {
        'statusCode': 200,
        'body': token
    }
