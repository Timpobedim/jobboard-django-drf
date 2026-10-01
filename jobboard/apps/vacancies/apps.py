from django.apps import AppConfig


class VacanciesAppConfig(AppConfig):
    name = "jobboard.apps.vacancies"
    label = "vacancies"
    verbose_name = "Vacancies"

    def ready(self) -> None:
        from jobboard.apps.vacancies import signals  # noqa: F401 — регистрация сигналов
