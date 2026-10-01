from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from jobboard.apps.authentication.models import User


def ensure_email_is_free(value: str, exclude_pk: int | None = None) -> str:
    email = value.lower()
    taken = User.objects.filter(email__iexact=email).exclude(pk=exclude_pk)
    if taken.exists():
        raise serializers.ValidationError("Пользователь с таким email уже зарегистрирован.")
    return email


class RegistrationSerializer(serializers.ModelSerializer):
    """Регистрация кандидата или компании: {"user": {"email", "username", "password", ...}}."""

    password = serializers.CharField(max_length=128, min_length=8, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)
    isCompany = serializers.BooleanField(write_only=True, required=False, default=False)
    companyName = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=120,
    )

    class Meta:
        model = User
        fields = ["email", "username", "password", "token", "isCompany", "companyName"]

    def validate_email(self, value: str) -> str:
        # UniqueValidator DRF сравнивает значение как есть; проверяем уникальность без учёта
        # регистра, иначе «Anna@Mail.ru» проходит валидацию и падает на ограничении БД.
        return ensure_email_is_free(value)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("isCompany") and not attrs.get("companyName", "").strip():
            raise serializers.ValidationError({"companyName": "Укажите название компании."})

        candidate = User(username=attrs.get("username", ""), email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as password_error:
            raise serializers.ValidationError(
                {"password": password_error.messages}
            ) from password_error

        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        is_company = validated_data.pop("isCompany", False)
        company_name = validated_data.pop("companyName", "").strip()

        with transaction.atomic():
            user = User.objects.create_user(**validated_data)
            if is_company:
                user.profile.is_company = True
                user.profile.company_name = company_name
                user.profile.save(update_fields=["is_company", "company_name", "updated_at"])

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        email = attrs["email"].lower()
        password = attrs["password"]

        user = authenticate(username=email, password=password)
        if user is None:
            raise serializers.ValidationError("Неверный email или пароль.")

        if not user.is_active:
            raise serializers.ValidationError("Пользователь деактивирован.")

        return {"email": user.email, "username": user.username, "token": user.token}


class UserSerializer(serializers.ModelSerializer):
    """Текущий пользователь: чтение и частичное обновление, включая поля профиля."""

    password = serializers.CharField(max_length=128, min_length=8, write_only=True, required=False)
    bio = serializers.CharField(source="profile.bio", required=False, allow_blank=True)
    image = serializers.URLField(source="profile.image", required=False, allow_blank=True)
    isCompany = serializers.BooleanField(source="profile.is_company", read_only=True)
    companyName = serializers.CharField(
        source="profile.company_name",
        required=False,
        allow_blank=True,
        max_length=120,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "password",
            "token",
            "bio",
            "image",
            "isCompany",
            "companyName",
        )
        read_only_fields = ("token",)

    def validate_email(self, value: str) -> str:
        return ensure_email_is_free(value, exclude_pk=self.instance.pk if self.instance else None)

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password", None)
        profile_data: dict[str, Any] = validated_data.pop("profile", {})

        with transaction.atomic():
            for key, value in validated_data.items():
                setattr(instance, key, value)

            if password is not None:
                instance.set_password(password)

            instance.save()

            for key, value in profile_data.items():
                setattr(instance.profile, key, value)

            instance.profile.save()

        return instance
