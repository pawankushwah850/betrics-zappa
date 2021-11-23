from django.urls import path, include
from .views import BookSubscription

urlpatterns = [
    # path("user/", UserCrud.as_view(), name="user_crud"),
    path("nfl/BookSubscription", BookSubscription.as_view(), name="BookSubscription")
]
