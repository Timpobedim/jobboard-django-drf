from django.urls import path

from jobboard.apps.authentication.views import (
    LoginAPIView,
    RegistrationAPIView,
    UserRetrieveUpdateAPIView,
)

app_name = "authentication"

urlpatterns = [
    path("user", UserRetrieveUpdateAPIView.as_view(), name="current-user"),
    path("users", RegistrationAPIView.as_view(), name="register"),
    path("users/login", LoginAPIView.as_view(), name="login"),
]
