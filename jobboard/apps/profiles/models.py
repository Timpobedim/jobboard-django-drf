from typing import TYPE_CHECKING

from django.db import models

from jobboard.apps.core.models import TimestampedModel

if TYPE_CHECKING:
    from jobboard.apps.vacancies.models import Vacancy


class Profile(TimestampedModel):
    """Публичный профиль: кандидат или компания-работодатель.

    Подписки — связь «многие ко многим» профиля с самим собой, а избранное —
    связь профиля с вакансиями. Добавлен признак компании: публиковать вакансии могут только
    профили компаний.
    """

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True)
    image = models.URLField(blank=True)
    is_company = models.BooleanField(default=False)
    company_name = models.CharField(max_length=120, blank=True)
    follows = models.ManyToManyField(
        "self",
        related_name="followed_by",
        symmetrical=False,
        blank=True,
    )
    saved_vacancies = models.ManyToManyField(
        "vacancies.Vacancy",
        related_name="saved_by",
        blank=True,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return str(self.user.username)

    def follow(self, profile: "Profile") -> None:
        self.follows.add(profile)

    def unfollow(self, profile: "Profile") -> None:
        self.follows.remove(profile)

    def is_following(self, profile: "Profile") -> bool:
        return self.follows.filter(pk=profile.pk).exists()

    def save_vacancy(self, vacancy: "Vacancy") -> None:
        self.saved_vacancies.add(vacancy)

    def unsave_vacancy(self, vacancy: "Vacancy") -> None:
        self.saved_vacancies.remove(vacancy)

    def has_saved(self, vacancy: "Vacancy") -> bool:
        return self.saved_vacancies.filter(pk=vacancy.pk).exists()
