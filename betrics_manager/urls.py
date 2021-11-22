from django.urls import path, include
from .views import BookSubscription

urlpatterns = [
    path("nfl/BookSubscription", BookSubscription.as_view(), name="BookSubscription")
]
