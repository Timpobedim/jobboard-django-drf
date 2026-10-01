from typing import Any

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from jobboard.apps.authentication.models import User
from jobboard.apps.vacancies.models import Experience, Vacancy
from tests.conftest import MakeUser, MakeVacancy, authorize

pytestmark = pytest.mark.django_db

LIST_URL = "vacancies:vacancy-list"
DETAIL_URL = "vacancies:vacancy-detail"


def vacancy_payload(**overrides: Any) -> dict[str, Any]:
    vacancy = {
        "title": "Junior Python-разработчик",
        "description": "Бэкенд сервиса доставки",
        "body": "Django, PostgreSQL, код-ревью от наставника",
        "salaryFrom": 90000,
        "salaryTo": 130000,
        "city": "Москва",
        "remote": True,
        "experience": "noExperience",
        "skillList": ["Python", "django", " PostgreSQL ", "python"],
    }
    vacancy.update(overrides)
    return {"vacancy": vacancy}


def slugs(response: Any) -> list[str]:
    return [item["slug"] for item in response.json()["vacancies"]]


def test_company_creates_vacancy(api_client: APIClient, company: User) -> None:
    authorize(api_client, company)

    response = api_client.post(reverse(LIST_URL), vacancy_payload())

    assert response.status_code == status.HTTP_201_CREATED
    vacancy = response.json()["vacancy"]
    assert vacancy["slug"].startswith("junior-python-razrabotchik-")
    assert vacancy["skillList"] == ["django", "postgresql", "python"]
    assert vacancy["company"]["companyName"] == "ТехноСтарт"
    assert vacancy["saved"] is False
    assert vacancy["savedCount"] == 0
    assert vacancy["salaryFrom"] == 90000


def test_only_companies_can_publish(api_client: APIClient, candidate: User) -> None:
    anonymous = api_client.post(reverse(LIST_URL), vacancy_payload())
    authorize(api_client, candidate)
    as_candidate = api_client.post(reverse(LIST_URL), vacancy_payload())

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert as_candidate.status_code == status.HTTP_403_FORBIDDEN
    assert "errors" in as_candidate.json()


@pytest.mark.parametrize(
    "overrides",
    [
        {"salaryFrom": 200000, "salaryTo": 100000},
        {"experience": "lead"},
        {"skillList": "python"},
        {"skillList": [f"skill-{index}" for index in range(16)]},
        {"title": ""},
    ],
)
def test_vacancy_validation(
    api_client: APIClient, company: User, overrides: dict[str, Any]
) -> None:
    authorize(api_client, company)

    response = api_client.post(reverse(LIST_URL), vacancy_payload(**overrides))

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_retrieve_and_404(api_client: APIClient, make_vacancy: MakeVacancy) -> None:
    vacancy = make_vacancy(skills=["python"])

    found = api_client.get(reverse(DETAIL_URL, args=[vacancy.slug]))
    missing = api_client.get(reverse(DETAIL_URL, args=["no-such-vacancy"]))

    assert found.status_code == status.HTTP_200_OK
    assert found.json()["vacancy"]["title"] == "Junior Python-разработчик"
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert "vacancy" in missing.json()["errors"]


def test_owner_updates_vacancy_and_slug_stays_stable(
    api_client: APIClient,
    company: User,
    make_vacancy: MakeVacancy,
) -> None:
    vacancy = make_vacancy(skills=["python", "django"])
    authorize(api_client, company)

    response = api_client.put(
        reverse(DETAIL_URL, args=[vacancy.slug]),
        {"vacancy": {"title": "Python-разработчик (стажёр)", "skillList": ["fastapi"]}},
    )
    salary_conflict = api_client.patch(
        reverse(DETAIL_URL, args=[vacancy.slug]),
        {"vacancy": {"salaryFrom": 500000, "salaryTo": 100000}},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["vacancy"]["slug"] == vacancy.slug
    assert response.json()["vacancy"]["title"] == "Python-разработчик (стажёр)"
    assert response.json()["vacancy"]["skillList"] == ["fastapi"]
    assert salary_conflict.status_code == status.HTTP_400_BAD_REQUEST


def test_other_company_can_not_modify_vacancy(
    api_client: APIClient,
    make_user: MakeUser,
    make_vacancy: MakeVacancy,
) -> None:
    vacancy = make_vacancy()
    rival = make_user("rival", company_name="Конкурент")
    authorize(api_client, rival)

    update = api_client.put(reverse(DETAIL_URL, args=[vacancy.slug]), {"vacancy": {"title": "X"}})
    delete = api_client.delete(reverse(DETAIL_URL, args=[vacancy.slug]))

    assert update.status_code == status.HTTP_403_FORBIDDEN
    assert delete.status_code == status.HTTP_403_FORBIDDEN


def test_owner_deletes_vacancy(
    api_client: APIClient,
    company: User,
    make_vacancy: MakeVacancy,
) -> None:
    vacancy = make_vacancy()
    authorize(api_client, company)

    deleted = api_client.delete(reverse(DETAIL_URL, args=[vacancy.slug]))

    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert deleted.content == b""
    assert not Vacancy.objects.filter(pk=vacancy.pk).exists()


def test_list_is_paginated_newest_first(api_client: APIClient, make_vacancy: MakeVacancy) -> None:
    created = [make_vacancy(f"Вакансия {index}") for index in range(5)]

    response = api_client.get(reverse(LIST_URL), {"limit": 2, "offset": 1})

    assert response.json()["vacanciesCount"] == 5
    assert slugs(response) == [created[3].slug, created[2].slug]


def test_list_filters(
    api_client: APIClient,
    candidate: User,
    make_user: MakeUser,
    make_vacancy: MakeVacancy,
) -> None:
    other = make_user("datalab", company_name="ДатаЛаб")
    python_msk = make_vacancy(
        "Python",
        skills=["python"],
        city="Москва",
        remote=False,
        salary_from=80000,
        salary_to=120000,
    )
    sql_remote = make_vacancy(
        "SQL",
        owner=other,
        skills=["sql"],
        city="Казань",
        remote=True,
        experience=Experience.BETWEEN_1_AND_3,
        salary_from=150000,
    )
    candidate.profile.save_vacancy(sql_remote)

    def filtered(**params: Any) -> list[str]:
        return slugs(api_client.get(reverse(LIST_URL), params))

    assert filtered(skill="PYTHON") == [python_msk.slug]
    assert filtered(company="datalab") == [sql_remote.slug]
    assert filtered(saved="candidate") == [sql_remote.slug]
    # SQLite сворачивает регистр в LIKE только для ASCII, поэтому здесь регистр совпадает;
    # регистронезависимость для кириллицы проверяет отдельный тест на PostgreSQL ниже.
    assert filtered(city="Моск") == [python_msk.slug]
    assert filtered(remote="true") == [sql_remote.slug]
    assert filtered(remote="false") == [python_msk.slug]
    assert filtered(experience="between1And3") == [sql_remote.slug]
    assert filtered(salaryMin=130000) == [sql_remote.slug]
    assert filtered(salaryMin=100000) == [sql_remote.slug, python_msk.slug]


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="в SQLite LIKE не сворачивает регистр кириллицы",
)
def test_city_filter_ignores_cyrillic_case_on_postgres(
    api_client: APIClient,
    make_vacancy: MakeVacancy,
) -> None:
    vacancy = make_vacancy(city="Санкт-Петербург")

    response = api_client.get(reverse(LIST_URL), {"city": "санкт"})

    assert slugs(response) == [vacancy.slug]


@pytest.mark.parametrize(
    "params",
    [{"remote": "maybe"}, {"experience": "lead"}, {"salaryMin": "много"}],
)
def test_invalid_filters(api_client: APIClient, params: dict[str, str]) -> None:
    response = api_client.get(reverse(LIST_URL), params)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_saved_count_is_not_distorted_by_saved_filter(
    api_client: APIClient,
    candidate: User,
    make_user: MakeUser,
    make_vacancy: MakeVacancy,
) -> None:
    vacancy = make_vacancy()
    for index in range(3):
        make_user(f"fan{index}").profile.save_vacancy(vacancy)
    candidate.profile.save_vacancy(vacancy)

    response = api_client.get(reverse(LIST_URL), {"saved": "candidate"})

    assert response.json()["vacancies"][0]["savedCount"] == 4


def test_save_and_unsave(api_client: APIClient, candidate: User, make_vacancy: MakeVacancy) -> None:
    vacancy = make_vacancy()
    url = reverse("vacancies:save", args=[vacancy.slug])
    anonymous = api_client.post(url)
    authorize(api_client, candidate)

    saved = api_client.post(url)
    listed = api_client.get(reverse(LIST_URL))
    unsaved = api_client.delete(url)
    missing = api_client.post(reverse("vacancies:save", args=["nope"]))

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert saved.status_code == status.HTTP_201_CREATED
    assert saved.json()["vacancy"]["saved"] is True
    assert saved.json()["vacancy"]["savedCount"] == 1
    assert listed.json()["vacancies"][0]["saved"] is True
    assert unsaved.json()["vacancy"]["saved"] is False
    assert unsaved.json()["vacancy"]["savedCount"] == 0
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_feed_shows_only_followed_companies(
    api_client: APIClient,
    candidate: User,
    company: User,
    make_user: MakeUser,
    make_vacancy: MakeVacancy,
) -> None:
    ignored_company = make_user("ignored", company_name="Игнор")
    followed_vacancy = make_vacancy("От подписки")
    make_vacancy("Без подписки", owner=ignored_company)
    candidate.profile.follow(company.profile)
    authorize(api_client, candidate)

    response = api_client.get(reverse("vacancies:feed"))

    assert slugs(response) == [followed_vacancy.slug]
    assert response.json()["vacancies"][0]["company"]["following"] is True


def test_feed_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("vacancies:feed"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_has_no_n_plus_one(
    api_client: APIClient,
    candidate: User,
    make_vacancy: MakeVacancy,
    django_assert_max_num_queries: Any,
) -> None:
    for index in range(10):
        vacancy = make_vacancy(f"Вакансия {index}", skills=["python", "sql"])
        candidate.profile.save_vacancy(vacancy)
    authorize(api_client, candidate)

    # аутентификация + COUNT для пагинации + страница с аннотациями + prefetch навыков
    with django_assert_max_num_queries(5):
        response = api_client.get(reverse(LIST_URL))

    assert len(response.json()["vacancies"]) == 10


def test_openapi_schema_is_generated(api_client: APIClient, db: None) -> None:
    response = api_client.get(reverse("schema"))

    assert response.status_code == status.HTTP_200_OK
    assert b"JuniorJobs API" in response.content
