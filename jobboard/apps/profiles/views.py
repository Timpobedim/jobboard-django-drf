from typing import Any

from rest_framework import serializers, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jobboard.apps.profiles.exceptions import ProfileDoesNotExistError
from jobboard.apps.profiles.models import Profile
from jobboard.apps.profiles.renderers import ProfileJSONRenderer
from jobboard.apps.profiles.serializers import ProfileSerializer


def _get_profile_or_404(username: str) -> Profile:
    try:
        return Profile.objects.select_related("user").get(user__username=username)
    except Profile.DoesNotExist as missing:
        raise ProfileDoesNotExistError from missing


class ProfileRetrieveAPIView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    queryset = Profile.objects.select_related("user")
    renderer_classes = (ProfileJSONRenderer,)
    serializer_class = ProfileSerializer

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        profile = _get_profile_or_404(kwargs["username"])
        serializer = self.serializer_class(profile, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileFollowAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)
    serializer_class = ProfileSerializer

    def post(self, request: Request, username: str) -> Response:
        follower = request.user.profile
        followee = _get_profile_or_404(username)

        if follower.pk == followee.pk:
            raise serializers.ValidationError("Нельзя подписаться на самого себя.")

        follower.follow(followee)
        serializer = self.serializer_class(followee, context={"request": request})

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request: Request, username: str) -> Response:
        follower = request.user.profile
        followee = _get_profile_or_404(username)

        follower.unfollow(followee)
        serializer = self.serializer_class(followee, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)
