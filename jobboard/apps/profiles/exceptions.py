from rest_framework.exceptions import NotFound


class ProfileDoesNotExistError(NotFound):
    """Отсутствующий профиль — 404, а не 400."""

    default_detail = "Профиль не найден."
