from collections.abc import Callable, Iterable
from typing import Any

import pytest
from rest_framework.test import APIClient

from jobboard.apps.authentication.models import User
from jobboard.apps.vacancies.models import Skill, Vacancy

MakeUser = Callable[..., User]
MakeVacancy = Callable[..., Vacancy]


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings: Any) -> None:
    """MD5 только в тестах: bcrypt/PBKDF2 на каждом пользователе заметно замедляют прогон."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def authorize(client: APIClient, user: User) -> APIClient:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user.token}")
    return client


@pytest.fixture
def make_user(db: None) -> MakeUser:
    def _make_user(
        username: str,
        *,
        company_name: str | None = None,
        password: str = "password123",
    ) -> User:
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
        )
        if company_name:
            user.profile.is_company = True
            user.profile.company_name = company_name
            user.profile.save()
        return user

    return _make_user


@pytest.fixture
def company(make_user: MakeUser) -> User:
    return make_user("techstart", company_name="ТехноСтарт")


@pytest.fixture
def candidate(make_user: MakeUser) -> User:
    return make_user("candidate")


@pytest.fixture
def make_vacancy(company: User) -> MakeVacancy:
    def _make_vacancy(
        title: str = "Junior Python-разработчик",
        *,
        owner: User | None = None,
        skills: Iterable[str] = (),
        **fields: Any,
    ) -> Vacancy:
        values: dict[str, Any] = {
            "description": "Разработка внутренних сервисов",
            "body": "Полное описание вакансии",
        }
        values.update(fields)
        vacancy = Vacancy.objects.create(title=title, company=(owner or company).profile, **values)
        vacancy.skills.set([Skill.objects.get_or_create(name=name)[0] for name in skills])
        return vacancy

    return _make_vacancy
