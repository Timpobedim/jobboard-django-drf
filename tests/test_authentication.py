from datetime import UTC, datetime, timedelta

import jwt
import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from jobboard.apps.authentication.models import User
from tests.conftest import MakeUser, authorize

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "Str0ng-Pass-2026"


def test_candidate_registration(api_client: APIClient) -> None:
    payload = {
        "user": {"email": "Maria@Example.com", "username": "maria", "password": STRONG_PASSWORD}
    }

    response = api_client.post(reverse("authentication:register"), payload)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()["user"]
    assert body["email"] == "maria@example.com"
    assert body["token"]
    assert not User.objects.get(username="maria").profile.is_company


def test_company_registration_requires_company_name(api_client: APIClient) -> None:
    url = reverse("authentication:register")
    base = {"email": "hr@example.com", "username": "hr_team", "password": STRONG_PASSWORD}

    without_name = api_client.post(url, {"user": {**base, "isCompany": True}})
    with_name = api_client.post(
        url, {"user": {**base, "isCompany": True, "companyName": "ДатаЛаб"}}
    )

    assert without_name.status_code == status.HTTP_400_BAD_REQUEST
    assert "companyName" in without_name.json()["errors"]
    assert with_name.status_code == status.HTTP_201_CREATED
    profile = User.objects.get(username="hr_team").profile
    assert profile.is_company
    assert profile.company_name == "ДатаЛаб"


@pytest.mark.parametrize("weak_password", ["12345678", "password"])
def test_registration_rejects_weak_passwords(api_client: APIClient, weak_password: str) -> None:
    payload = {"user": {"email": "weak@example.com", "username": "weak", "password": weak_password}}

    response = api_client.post(reverse("authentication:register"), payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.json()["errors"]


def test_registration_rejects_taken_email_in_any_case(
    api_client: APIClient,
    candidate: User,
) -> None:
    payload = {
        "user": {
            "email": "CANDIDATE@example.com",
            "username": "other",
            "password": STRONG_PASSWORD,
        },
    }

    response = api_client.post(reverse("authentication:register"), payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.json()["errors"]


def test_login_returns_token(api_client: APIClient, candidate: User) -> None:
    payload = {"user": {"email": "Candidate@Example.com", "password": "password123"}}

    response = api_client.post(reverse("authentication:login"), payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user"]["username"] == "candidate"
    assert response.json()["user"]["token"]


def test_login_with_wrong_password(api_client: APIClient, candidate: User) -> None:
    payload = {"user": {"email": "candidate@example.com", "password": "wrong-password"}}

    response = api_client.post(reverse("authentication:login"), payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"errors": {"error": ["Неверный email или пароль."]}}


def test_current_user_requires_token(api_client: APIClient) -> None:
    response = api_client.get(reverse("authentication:current-user"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response["WWW-Authenticate"] == "Bearer"
    assert "errors" in response.json()


@pytest.mark.parametrize(
    "header", ["Bearer broken.token.value", "Token abc", "Bearer", "Bearer a b"]
)
def test_invalid_authorization_headers_are_rejected(api_client: APIClient, header: str) -> None:
    api_client.credentials(HTTP_AUTHORIZATION=header)

    response = api_client.get(reverse("authentication:current-user"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "payload",
    [
        {"id": 100500, "exp": datetime.now(UTC) + timedelta(days=1)},
        {"exp": datetime.now(UTC) + timedelta(days=1)},
    ],
)
def test_token_for_unknown_user_is_rejected(
    api_client: APIClient, payload: dict[str, object]
) -> None:
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = api_client.get(reverse("authentication:current-user"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_expired_and_deactivated_tokens_are_rejected(
    api_client: APIClient, candidate: User
) -> None:
    expired = jwt.encode(
        {"id": candidate.pk, "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
    expired_response = api_client.get(reverse("authentication:current-user"))

    candidate.is_active = False
    candidate.save()
    authorize(api_client, candidate)
    inactive_response = api_client.get(reverse("authentication:current-user"))

    assert expired_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert inactive_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_can_update_profile_fields_and_password(
    api_client: APIClient,
    candidate: User,
) -> None:
    authorize(api_client, candidate)

    response = api_client.put(
        reverse("authentication:current-user"),
        {
            "user": {
                "bio": "Ищу стажировку в backend",
                "image": "https://example.com/me.png",
                "password": "New-Str0ng-Pass",
            },
        },
    )
    login = APIClient().post(
        reverse("authentication:login"),
        {"user": {"email": "candidate@example.com", "password": "New-Str0ng-Pass"}},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user"]["bio"] == "Ищу стажировку в backend"
    assert response.json()["user"]["image"] == "https://example.com/me.png"
    assert login.status_code == status.HTTP_200_OK


def test_company_can_rename_itself(api_client: APIClient, make_user: MakeUser) -> None:
    company = make_user("datalab", company_name="ДатаЛаб")
    authorize(api_client, company)

    response = api_client.put(
        reverse("authentication:current-user"),
        {"user": {"companyName": "ДатаЛаб Групп", "email": "HR@DataLab.dev"}},
    )

    assert response.json()["user"]["companyName"] == "ДатаЛаб Групп"
    assert response.json()["user"]["email"] == "hr@datalab.dev"
    assert response.json()["user"]["isCompany"]


def test_create_user_requires_username_and_email(db: None) -> None:
    with pytest.raises(TypeError):
        User.objects.create_user(username="", email="x@example.com")
    with pytest.raises(TypeError):
        User.objects.create_user(username="x", email="")


def test_create_superuser(db: None) -> None:
    admin = User.objects.create_superuser("admin", "admin@example.com", "Adm1n-Pass")

    assert admin.is_superuser
    assert admin.is_staff
    assert str(admin) == "admin@example.com"
    assert admin.get_full_name() == admin.get_short_name() == "admin"
