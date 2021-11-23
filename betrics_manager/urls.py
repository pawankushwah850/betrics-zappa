from django.urls import path
from .views import BookSubscription, GetWeek, GetSportsbook, GetSportOdds, GetTeamData, WagerEvent

urlpatterns = [
    # path("user/", UserCrud.as_view(), name="user_crud"),
    path("nfl/getBookSubscription", BookSubscription.as_view(), name="getBookSubscription"),
    path("nfl/getSportsbook", GetSportsbook.as_view(), name="getSportsbook"),
    path("nfl/getWeek", GetWeek.as_view(), name="getWeek"),
    path("nfl/getSportOdds", GetSportOdds.as_view(), name="getSportOdds"),
    path("nfl/getTeamData", GetTeamData.as_view(), name="getTeamData"),
    path("nfl/wagerEvent", WagerEvent.as_view(), name="wagerEvent"),
]
