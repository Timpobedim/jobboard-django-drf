from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver
from slugify import slugify

from jobboard.apps.core.utils import generate_random_string
from jobboard.apps.vacancies.models import Vacancy

MAXIMUM_SLUG_LENGTH = 255
SUFFIX_LENGTH = 6


@receiver(pre_save, sender=Vacancy)
def add_slug_to_vacancy_if_not_exists(
    sender: type[Vacancy], instance: Vacancy, **kwargs: Any
) -> None:
    """Slug создаётся один раз и не меняется при смене заголовка — ссылки на вакансию стабильны.

    django.utils.text.slugify просто выбрасывает кириллицу («Python-разработчик» → «python»),
    поэтому заголовок транслитерируется, а случайный суффикс гарантирует уникальность.
    """
    if instance.slug:
        return

    base = slugify(instance.title, max_length=MAXIMUM_SLUG_LENGTH - SUFFIX_LENGTH - 1) or "vacancy"
    instance.slug = f"{base}-{generate_random_string(size=SUFFIX_LENGTH)}"
