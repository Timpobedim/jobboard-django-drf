from django.apps import AppConfig


class AuthenticationAppConfig(AppConfig):
    name = "jobboard.apps.authentication"
    label = "authentication"
    verbose_name = "Authentication"

    def ready(self) -> None:
        from jobboard.apps.authentication import signals  # noqa: F401 — регистрация сигналов
