from lambda_functions.sportbooks import book_subscription, getSportsBook
from lambda_functions import nfl_get_schedule, nfl_team_data, wager_event

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class BookSubscription(APIView):

    def get(self, request):
        payload = {
            "http_method": request.method,
            "user": request.user
        }
        response = book_subscription.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)

    def put(self, request):
        payload = {
            "http_method": request.method,
            "body": request.body,
            "user": request.user
        }
        response = book_subscription.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)


class GetSportsbook(APIView):

    def get(self, request):
        payload = {
            "http_method": request.method,
            "user": request.user
        }
        response = getSportsBook.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)


class GetWeek(APIView):

    def get(self, request):
        payload = {
            "http_method": request.method,
            "user": request.user
        }
        response = nfl_get_schedule.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)


class GetSportOdds(APIView):

    def get(self, request):
        book = request.GET.get("book")
        week = request.GET.get("week")

        payload = {
            "http_method": request.method,
            "user": request.user,
            "week": week,
            "book": book
        }
        response = nfl_get_schedule.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)


class GetTeamData(APIView):

    def get(self, request):
        team = request.GET.get("team")
        payload = {
            "http_method": request.method,
            "user": request.user,
            "team": team
        }
        response = nfl_team_data.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)


class WagerEvent(APIView):

    def get(self, request):
        payload = {
            "http_method": request.method,
            "user": request.user,
            "body": request.body
        }
        response = wager_event.lambda_handler(payload)
        return Response(response, status=status.HTTP_200_OK)
