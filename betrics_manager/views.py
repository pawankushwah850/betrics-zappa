from lambda_functions.sportbooks import book_subscription

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
import json


class BookSubscription(APIView):

    def get(self, request):
        print(request.user.email)
        payload = {
            "http_method": request.method
        }
        response = book_subscription.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)
