from django.shortcuts import render
from rest_framework.views import APIView
from lambda_functions.sportbooks import book_subscription
from lambda_functions.user import user_crud
from rest_framework.response import Response
from rest_framework import status
import json


# Create your views here.


class UserCrud(APIView):

    def get(self, request):
        pass

    def post(self, request):
        data = request.body
        payload = {
            "http_method": request.method,
            "body": json.loads(data.decode("utf-8"))
        }
        response = user_crud.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)


class BookSubscription(APIView):

    def get(self, request):
        payload = {
            "http_method": request.method
        }
        response = book_subscription.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)
