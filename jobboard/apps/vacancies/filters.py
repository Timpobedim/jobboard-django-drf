from collections.abc import Mapping

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from jobboard.apps.vacancies.models import Experience, VacancyQuerySet

TRUE_VALUES = {"1", "true", "yes"}
FALSE_VALUES = {"0", "false", "no"}


def _parse_bool(value: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValidationError({field: "Ожидается true или false."})


def filter_vacancies(queryset: VacancyQuerySet, params: Mapping[str, str]) -> VacancyQuerySet:
    """Фильтры списка вакансий из query-параметров.

    Автор, навык, избранное, город, удалёнка, опыт и минимальная зарплата.
    """
    if skill := params.get("skill"):
        queryset = queryset.filter(skills__name=skill.strip().lower())

    if company := params.get("company"):
        queryset = queryset.filter(company__user__username=company)

    if saved := params.get("saved"):
        queryset = queryset.filter(saved_by__user__username=saved)

    if city := params.get("city"):
        queryset = queryset.filter(city__icontains=city.strip())

    if (remote := params.get("remote")) is not None:
        queryset = queryset.filter(remote=_parse_bool(remote, "remote"))

    if experience := params.get("experience"):
        if experience not in Experience.values:
            raise ValidationError(
                {"experience": f"Допустимые значения: {', '.join(Experience.values)}."}
            )
        queryset = queryset.filter(experience=experience)

    if salary_min := params.get("salaryMin"):
        try:
            minimum = int(salary_min)
        except ValueError as parse_error:
            raise ValidationError({"salaryMin": "Ожидается целое число."}) from parse_error
        # Подходит, если верхняя граница не ниже минимума, а при её отсутствии — нижняя.
        queryset = queryset.filter(
            Q(salary_to__gte=minimum) | Q(salary_to__isnull=True, salary_from__gte=minimum),
        )

    return queryset
