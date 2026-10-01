import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from jobboard.apps.authentication.models import User
from tests.conftest import authorize

pytestmark = pytest.mark.django_db


def test_anyone_can_see_company_profile(api_client: APIClient, company: User) -> None:
    response = api_client.get(reverse("profiles:detail", args=[company.username]))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "profile": {
            "username": "techstart",
            "bio": "",
            "image": None,
            "isCompany": True,
            "companyName": "ТехноСтарт",
            "following": False,
        },
    }


def test_unknown_profile_returns_404(api_client: APIClient) -> None:
    response = api_client.get(reverse("profiles:detail", args=["nobody"]))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"errors": {"profile": "Профиль не найден."}}


def test_candidate_can_follow_and_unfollow_company(
    api_client: APIClient,
    candidate: User,
    company: User,
) -> None:
    authorize(api_client, candidate)
    url = reverse("profiles:follow", args=[company.username])

    followed = api_client.post(url)
    detail = api_client.get(reverse("profiles:detail", args=[company.username]))
    unfollowed = api_client.delete(url)

    assert followed.status_code == status.HTTP_201_CREATED
    assert followed.json()["profile"]["following"]
    assert detail.json()["profile"]["following"]
    assert unfollowed.status_code == status.HTTP_200_OK
    assert not unfollowed.json()["profile"]["following"]


def test_follow_edge_cases(api_client: APIClient, candidate: User) -> None:
    anonymous = api_client.post(reverse("profiles:follow", args=[candidate.username]))
    authorize(api_client, candidate)
    self_follow = api_client.post(reverse("profiles:follow", args=[candidate.username]))
    unknown = api_client.delete(reverse("profiles:follow", args=["nobody"]))

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert self_follow.status_code == status.HTTP_400_BAD_REQUEST
    assert unknown.status_code == status.HTTP_404_NOT_FOUND
