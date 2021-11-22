from django.shortcuts import render
from rest_framework.views import APIView
from lambda_functions.sportbooks import book_subscription
from rest_framework.response import Response
from rest_framework import status


# Create your views here.

class BookSubscription(APIView):

    def get(self, request):
        payload = {
            "http_method": request.method
        }
        response = book_subscription.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)
