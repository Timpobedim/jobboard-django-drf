from django.urls import path

from jobboard.apps.profiles.views import ProfileFollowAPIView, ProfileRetrieveAPIView

app_name = "profiles"

urlpatterns = [
    path("profiles/<str:username>", ProfileRetrieveAPIView.as_view(), name="detail"),
    path("profiles/<str:username>/follow", ProfileFollowAPIView.as_view(), name="follow"),
]
