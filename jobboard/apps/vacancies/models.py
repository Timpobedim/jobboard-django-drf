from typing import Self

from django.db import models
from django.db.models import Count, Exists, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from jobboard.apps.core.models import TimestampedModel
from jobboard.apps.profiles.models import Profile


class Experience(models.TextChoices):
    """Значения совпадают с фильтром опыта в API hh.ru — привычно для рынка РФ."""

    NO_EXPERIENCE = "noExperience", "Нет опыта"
    BETWEEN_1_AND_3 = "between1And3", "От 1 до 3 лет"
    BETWEEN_3_AND_6 = "between3And6", "От 3 до 6 лет"
    MORE_THAN_6 = "moreThan6", "Более 6 лет"


class Skill(TimestampedModel):
    """Навык из требований вакансии."""

    name = models.CharField(max_length=40, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class VacancyQuerySet(models.QuerySet):
    def with_viewer_state(self, profile: Profile | None) -> Self:
        """Одним запросом добирает всё, что нужно для ответа, с точки зрения смотрящего профиля.

        «В избранном ли», счётчик избранного и подписка на автора — не отдельные запросы
        для каждой вакансии (N+1), а аннотации: счётчик —
        коррелированный подзапрос (не ломается при фильтрах по тем же связям), флаги — EXISTS.
        """
        saved_through = Profile.saved_vacancies.through
        follows_through = Profile.follows.through

        saved_count = Subquery(
            saved_through.objects.filter(vacancy_id=OuterRef("pk"))
            .order_by()
            .values("vacancy_id")
            .annotate(total=Count("*"))
            .values("total")[:1],
        )
        queryset = (
            self.select_related("company__user")
            .prefetch_related("skills")
            .annotate(saved_count=Coalesce(saved_count, 0))
        )

        if profile is None:
            return queryset.annotate(is_saved=Value(False), company_followed=Value(False))

        return queryset.annotate(
            is_saved=Exists(
                saved_through.objects.filter(profile_id=profile.pk, vacancy_id=OuterRef("pk")),
            ),
            company_followed=Exists(
                follows_through.objects.filter(
                    from_profile_id=profile.pk,
                    to_profile_id=OuterRef("company_id"),
                ),
            ),
        )


class Vacancy(TimestampedModel):
    slug = models.SlugField(db_index=True, max_length=255, unique=True)
    title = models.CharField(db_index=True, max_length=255)
    description = models.TextField()
    body = models.TextField()
    salary_from = models.PositiveIntegerField(null=True, blank=True)
    salary_to = models.PositiveIntegerField(null=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    remote = models.BooleanField(default=False)
    experience = models.CharField(
        max_length=20,
        choices=Experience.choices,
        default=Experience.NO_EXPERIENCE,
    )
    company = models.ForeignKey(
        "profiles.Profile",
        on_delete=models.CASCADE,
        related_name="vacancies",
    )
    skills = models.ManyToManyField(Skill, related_name="vacancies", blank=True)

    objects = VacancyQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "vacancies"
        constraints = [
            models.CheckConstraint(
                condition=Q(salary_from__isnull=True)
                | Q(salary_to__isnull=True)
                | Q(salary_from__lte=F("salary_to")),
                name="vacancy_salary_range_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Question(TimestampedModel):
    """Вопрос кандидата к вакансии."""

    body = models.TextField()
    vacancy = models.ForeignKey(Vacancy, related_name="questions", on_delete=models.CASCADE)
    author = models.ForeignKey(
        "profiles.Profile",
        related_name="questions",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return self.body[:50]
