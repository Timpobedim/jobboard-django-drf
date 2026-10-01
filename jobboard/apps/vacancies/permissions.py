from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from jobboard.apps.vacancies.models import Question, Vacancy


class IsCompanyOrReadOnly(BasePermission):
    message = "Публиковать и изменять вакансии могут только аккаунты компаний."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True

        return bool(request.user.is_authenticated and request.user.profile.is_company)


class IsVacancyOwnerOrReadOnly(BasePermission):
    message = "Изменять вакансию может только компания, которая её разместила."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True

        return isinstance(obj, Vacancy) and obj.company_id == request.user.profile.pk


class IsQuestionAuthorOrVacancyOwner(BasePermission):
    """Удалить вопрос может его автор или компания-владелец вакансии (модерация).

    Проверяются и автор, и принадлежность вопроса вакансии из URL.
    """

    message = "Удалить вопрос может только его автор или компания, разместившая вакансию."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not isinstance(obj, Question):
            return False

        profile_id = request.user.profile.pk
        return profile_id in {obj.author_id, obj.vacancy.company_id}
