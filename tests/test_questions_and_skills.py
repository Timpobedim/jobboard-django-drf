import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from jobboard.apps.authentication.models import User
from jobboard.apps.vacancies.models import Question, Vacancy
from tests.conftest import MakeUser, MakeVacancy, authorize

pytestmark = pytest.mark.django_db


@pytest.fixture
def vacancy(make_vacancy: MakeVacancy) -> Vacancy:
    return make_vacancy(skills=["python"])


def ask(client: APIClient, vacancy: Vacancy, text: str = "Есть ли наставник?") -> Question:
    response = client.post(
        reverse("vacancies:questions", args=[vacancy.slug]),
        {"question": {"body": text}},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return Question.objects.get(pk=response.json()["question"]["id"])


def test_candidate_asks_and_anyone_reads(
    api_client: APIClient,
    candidate: User,
    vacancy: Vacancy,
) -> None:
    ask(authorize(api_client, candidate), vacancy)

    response = APIClient().get(reverse("vacancies:questions", args=[vacancy.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["questionsCount"] == 1
    assert response.json()["questions"][0]["author"]["username"] == "candidate"


def test_asking_requires_auth_and_existing_vacancy(
    api_client: APIClient,
    candidate: User,
    vacancy: Vacancy,
) -> None:
    anonymous = api_client.post(
        reverse("vacancies:questions", args=[vacancy.slug]),
        {"question": {"body": "?"}},
    )
    authorize(api_client, candidate)
    missing = api_client.post(
        reverse("vacancies:questions", args=["no-such-vacancy"]),
        {"question": {"body": "?"}},
    )

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_author_and_vacancy_owner_can_delete_question(
    api_client: APIClient,
    candidate: User,
    company: User,
    vacancy: Vacancy,
) -> None:
    first = ask(authorize(APIClient(), candidate), vacancy)
    second = ask(authorize(APIClient(), candidate), vacancy, "Какой график?")

    by_author = authorize(api_client, candidate).delete(
        reverse("vacancies:question-detail", args=[vacancy.slug, first.pk]),
    )
    by_owner = authorize(APIClient(), company).delete(
        reverse("vacancies:question-detail", args=[vacancy.slug, second.pk]),
    )

    assert by_author.status_code == status.HTTP_204_NO_CONTENT
    assert by_owner.status_code == status.HTTP_204_NO_CONTENT
    assert not Question.objects.exists()


def test_stranger_can_not_delete_question(
    candidate: User,
    make_user: MakeUser,
    vacancy: Vacancy,
) -> None:
    question = ask(authorize(APIClient(), candidate), vacancy)
    stranger = make_user("stranger")

    response = authorize(APIClient(), stranger).delete(
        reverse("vacancies:question-detail", args=[vacancy.slug, question.pk]),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Question.objects.filter(pk=question.pk).exists()


def test_question_is_looked_up_within_vacancy_from_url(
    candidate: User,
    make_vacancy: MakeVacancy,
    vacancy: Vacancy,
) -> None:
    question = ask(authorize(APIClient(), candidate), vacancy)
    other_vacancy = make_vacancy("Другая вакансия")

    response = authorize(APIClient(), candidate).delete(
        reverse("vacancies:question-detail", args=[other_vacancy.slug, question.pk]),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_skills_are_listed_sorted(api_client: APIClient, make_vacancy: MakeVacancy) -> None:
    make_vacancy("A", skills=["sql", "python"])
    make_vacancy("B", skills=["airflow", "python"])

    response = api_client.get(reverse("vacancies:skills"))

    assert response.json() == {"skills": ["airflow", "python", "sql"]}


def test_seed_demo_is_idempotent() -> None:
    call_command("seed_demo")
    counts = (User.objects.count(), Vacancy.objects.count(), Question.objects.count())

    call_command("seed_demo")

    assert counts == (User.objects.count(), Vacancy.objects.count(), Question.objects.count())
    assert Vacancy.objects.filter(company__is_company=True).count() == counts[1] > 0
