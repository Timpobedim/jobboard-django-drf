"""Демо-данные: вымышленные компании, кандидаты, вакансии для джунов и вопросы к ним.

Запуск: python manage.py seed_demo  (повторный запуск ничего не дублирует)
"""

from dataclasses import dataclass, field
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from jobboard.apps.authentication.models import User
from jobboard.apps.vacancies.models import Experience, Question, Skill, Vacancy

DEMO_PASSWORD = "demo-password"  # noqa: S105 — пароль демо-аккаунтов из README

COMPANIES = {
    "techstart": ("ТехноСтарт", "Разрабатываем B2B-сервисы для ритейла"),
    "datalab": ("ДатаЛаб", "Аналитика и машинное обучение для логистики"),
    "cloudplus": ("Облако Плюс", "Облачная инфраструктура для малого бизнеса"),
}

CANDIDATES = {
    "maria_junior": "Закончила курс Python, собираю портфолио из pet-проектов",
    "oleg_qa": "Перехожу из ручного тестирования в автоматизацию",
}


@dataclass(frozen=True)
class DemoVacancy:
    company: str
    title: str
    description: str
    salary_from: int | None
    salary_to: int | None
    city: str
    remote: bool
    experience: str
    skills: list[str] = field(default_factory=list)


VACANCIES = [
    DemoVacancy(
        "techstart",
        "Junior Python-разработчик (Django)",
        "Бэкенд сервиса учёта заказов для розничных сетей",
        90_000,
        130_000,
        "Москва",
        True,
        Experience.NO_EXPERIENCE,
        ["python", "django", "postgresql", "git"],
    ),
    DemoVacancy(
        "techstart",
        "Стажёр backend-разработчик",
        "Оплачиваемая стажировка на 3 месяца с наставником",
        60_000,
        80_000,
        "Москва",
        False,
        Experience.NO_EXPERIENCE,
        ["python", "sql"],
    ),
    DemoVacancy(
        "techstart",
        "Python-разработчик интеграций",
        "Интеграции с CRM и маркетплейсами через REST API",
        120_000,
        170_000,
        "Екатеринбург",
        True,
        Experience.BETWEEN_1_AND_3,
        ["python", "fastapi", "rest", "bitrix24"],
    ),
    DemoVacancy(
        "datalab",
        "Junior аналитик данных",
        "Отчёты по логистике и поддержка дашбордов для операционной команды",
        70_000,
        100_000,
        "Санкт-Петербург",
        True,
        Experience.NO_EXPERIENCE,
        ["sql", "python", "pandas", "excel"],
    ),
    DemoVacancy(
        "datalab",
        "Junior Data Engineer",
        "Пайплайны загрузки данных о перевозках в хранилище",
        110_000,
        150_000,
        "Казань",
        True,
        Experience.BETWEEN_1_AND_3,
        ["python", "airflow", "clickhouse", "sql"],
    ),
    DemoVacancy(
        "datalab",
        "BI-аналитик (Power BI)",
        "Дашборды для руководителей складов",
        80_000,
        None,
        "Москва",
        True,
        Experience.NO_EXPERIENCE,
        ["sql", "power bi", "dax"],
    ),
    DemoVacancy(
        "cloudplus",
        "Junior DevOps-инженер",
        "Поддержка CI/CD и мониторинга клиентских окружений",
        80_000,
        110_000,
        "Новосибирск",
        False,
        Experience.NO_EXPERIENCE,
        ["linux", "docker", "git", "bash"],
    ),
    DemoVacancy(
        "cloudplus",
        "Инженер по автоматизации тестирования (Python)",
        "Автотесты API и UI для панели управления облаком",
        80_000,
        120_000,
        "",
        True,
        Experience.NO_EXPERIENCE,
        ["python", "pytest", "playwright"],
    ),
]

QUESTIONS = [
    (
        "Junior Python-разработчик (Django)",
        "maria_junior",
        "Рассматриваете кандидатов без коммерческого опыта, но с pet-проектами на GitHub?",
    ),
    (
        "Инженер по автоматизации тестирования (Python)",
        "oleg_qa",
        "Какой CI используете и сколько сейчас автотестов?",
    ),
]


class Command(BaseCommand):
    help = "Создаёт демо-данные: компании, кандидатов, вакансии и вопросы (идемпотентно)."

    def handle(self, *args: Any, **options: Any) -> None:
        with transaction.atomic():
            users = self._ensure_users()
            created = self._ensure_vacancies(users)
            if created:
                self._ensure_activity(users)

        self.stdout.write(
            self.style.SUCCESS(f"Готово: пользователей {len(users)}, новых вакансий {created}"),
        )

    def _ensure_users(self) -> dict[str, User]:
        users: dict[str, User] = {}
        for username, (company_name, bio) in COMPANIES.items():
            users[username] = self._get_or_create(username, bio, company_name)
        for username, bio in CANDIDATES.items():
            users[username] = self._get_or_create(username, bio, None)
        return users

    @staticmethod
    def _get_or_create(username: str, bio: str, company_name: str | None) -> User:
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create_user(username, f"{username}@juniorjobs.dev", DEMO_PASSWORD)
            user.profile.bio = bio
            user.profile.is_company = company_name is not None
            user.profile.company_name = company_name or ""
            user.profile.save()
        return user

    @staticmethod
    def _ensure_vacancies(users: dict[str, User]) -> int:
        created = 0
        for item in VACANCIES:
            company = users[item.company].profile
            if Vacancy.objects.filter(company=company, title=item.title).exists():
                continue
            vacancy = Vacancy.objects.create(
                company=company,
                title=item.title,
                description=item.description,
                body=f"{item.description}. Обучение внутри команды, код-ревью, гибкий график.",
                salary_from=item.salary_from,
                salary_to=item.salary_to,
                city=item.city,
                remote=item.remote,
                experience=item.experience,
            )
            vacancy.skills.set([Skill.objects.get_or_create(name=name)[0] for name in item.skills])
            created += 1
        return created

    @staticmethod
    def _ensure_activity(users: dict[str, User]) -> None:
        maria = users["maria_junior"].profile
        oleg = users["oleg_qa"].profile
        maria.follow(users["techstart"].profile)
        maria.follow(users["datalab"].profile)
        oleg.follow(users["cloudplus"].profile)

        for vacancy in Vacancy.objects.filter(skills__name="python").distinct():
            maria.save_vacancy(vacancy)

        for title, username, body in QUESTIONS:
            vacancy = Vacancy.objects.get(title=title)
            Question.objects.create(vacancy=vacancy, author=users[username].profile, body=body)
