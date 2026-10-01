from datetime import UTC, datetime
from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from jobboard.apps.core.models import TimestampedModel


class UserManager(BaseUserManager):
    def create_user(self, username: str, email: str, password: str | None = None) -> "User":
        if not username:
            raise TypeError("Users must have a username.")

        if not email:
            raise TypeError("Users must have an email address.")

        user: User = self.model(username=username, email=self.normalize_email(email).lower())
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username: str, email: str, password: str) -> "User":
        if password is None:
            raise TypeError("Superusers must have a password.")

        user = self.create_user(username, email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    username = models.CharField(db_index=True, max_length=40, unique=True)
    email = models.EmailField(db_index=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.email

    @property
    def token(self) -> str:
        return self._generate_jwt_token()

    def get_full_name(self) -> str:
        return self.username

    def get_short_name(self) -> str:
        return self.username

    def _generate_jwt_token(self) -> str:
        """JWT с id пользователя и сроком жизни из настроек.

        Срок считается не через strftime('%s') (не работает на Windows), а результат
        jwt.encode не декодируется из bytes — в PyJWT ≥ 2 это уже str.
        """
        payload: dict[str, Any] = {
            "id": self.pk,
            "exp": datetime.now(UTC) + settings.JWT_EXPIRATION,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
