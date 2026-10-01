from typing import Any

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.request import Request

from jobboard.apps.authentication.models import User


class JWTAuthentication(authentication.BaseAuthentication):
    """Аутентификация по заголовку «Authorization: Bearer <JWT>».

    jwt.decode вызывается с явным списком алгоритмов
    (обязателен в PyJWT ≥ 2 и защищает от подмены алгоритма), а метод authenticate_header
    заставляет DRF отвечать 401 с WWW-Authenticate вместо 403 на запрос без токена.
    """

    @property
    def authentication_header_prefix(self) -> str:
        prefix: str = settings.JWT_AUTH_HEADER_PREFIX
        return prefix

    def authenticate(self, request: Request) -> tuple[User, str] | None:
        auth_header = authentication.get_authorization_header(request).split()

        # Нет заголовка, только префикс или токен с пробелами — не пытаемся аутентифицировать.
        if len(auth_header) != 2:
            return None

        prefix = auth_header[0].decode("utf-8")
        token = auth_header[1].decode("utf-8")

        if prefix.lower() != self.authentication_header_prefix.lower():
            return None

        return self._authenticate_credentials(token)

    def authenticate_header(self, request: Request) -> str:
        return self.authentication_header_prefix

    def _authenticate_credentials(self, token: str) -> tuple[User, str]:
        try:
            payload: dict[str, Any] = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError as decode_error:
            raise exceptions.AuthenticationFailed("Недействительный токен.") from decode_error

        try:
            user = User.objects.select_related("profile").get(pk=payload["id"])
        except (User.DoesNotExist, KeyError) as lookup_error:
            raise exceptions.AuthenticationFailed(
                "Пользователь из токена не найден."
            ) from lookup_error

        if not user.is_active:
            raise exceptions.AuthenticationFailed("Пользователь деактивирован.")

        return user, token
