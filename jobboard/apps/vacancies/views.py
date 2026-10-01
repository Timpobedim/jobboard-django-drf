from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jobboard.apps.profiles.models import Profile
from jobboard.apps.vacancies.filters import filter_vacancies
from jobboard.apps.vacancies.models import Question, Skill, Vacancy, VacancyQuerySet
from jobboard.apps.vacancies.permissions import (
    IsCompanyOrReadOnly,
    IsQuestionAuthorOrVacancyOwner,
    IsVacancyOwnerOrReadOnly,
)
from jobboard.apps.vacancies.renderers import QuestionJSONRenderer, VacancyJSONRenderer
from jobboard.apps.vacancies.serializers import (
    QuestionSerializer,
    SkillSerializer,
    VacancySerializer,
)


def viewer_profile(request: Request) -> Profile | None:
    return request.user.profile if request.user.is_authenticated else None


class VacancyViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD вакансий, включая удаление (DestroyModelMixin)."""

    lookup_field = "slug"
    queryset = Vacancy.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsCompanyOrReadOnly, IsVacancyOwnerOrReadOnly)
    renderer_classes = (VacancyJSONRenderer,)
    serializer_class = VacancySerializer

    def get_queryset(self) -> VacancyQuerySet:
        queryset = Vacancy.objects.with_viewer_state(viewer_profile(self.request))
        if self.action == "list":
            queryset = filter_vacancies(queryset, self.request.query_params)
        return queryset

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context["company"] = self.request.user.profile
        return context

    def _reload(self, vacancy: Vacancy) -> Vacancy:
        """Перечитывает вакансию с аннотациями, чтобы ответ не делал лишних запросов."""
        return Vacancy.objects.with_viewer_state(viewer_profile(self.request)).get(pk=vacancy.pk)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data.get("vacancy", {}))
        serializer.is_valid(raise_exception=True)
        vacancy = serializer.save()

        return Response(
            self.get_serializer(self._reload(vacancy)).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # По спецификации RealWorld PUT обновляет только переданные поля.
        vacancy = self.get_object()
        serializer = self.get_serializer(
            vacancy, data=request.data.get("vacancy", {}), partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.get_serializer(self._reload(vacancy)).data, status=status.HTTP_200_OK)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.update(request, *args, **kwargs)


class VacancyFeedAPIView(generics.ListAPIView):
    """Вакансии компаний, на которые подписан пользователь."""

    permission_classes = (IsAuthenticated,)
    renderer_classes = (VacancyJSONRenderer,)
    serializer_class = VacancySerializer

    def get_queryset(self) -> QuerySet[Vacancy]:
        profile = self.request.user.profile
        return Vacancy.objects.with_viewer_state(profile).filter(company__followed_by=profile)


class VacancySaveAPIView(APIView):
    """Добавить вакансию в избранное (POST) или убрать из него (DELETE)."""

    permission_classes = (IsAuthenticated,)
    renderer_classes = (VacancyJSONRenderer,)
    serializer_class = VacancySerializer

    def _respond(self, request: Request, vacancy: Vacancy, code: int) -> Response:
        fresh = Vacancy.objects.with_viewer_state(request.user.profile).get(pk=vacancy.pk)
        serializer = self.serializer_class(fresh, context={"request": request})
        return Response(serializer.data, status=code)

    def post(self, request: Request, vacancy_slug: str) -> Response:
        vacancy = get_object_or_404(Vacancy, slug=vacancy_slug)
        request.user.profile.save_vacancy(vacancy)
        return self._respond(request, vacancy, status.HTTP_201_CREATED)

    def delete(self, request: Request, vacancy_slug: str) -> Response:
        vacancy = get_object_or_404(Vacancy, slug=vacancy_slug)
        request.user.profile.unsave_vacancy(vacancy)
        return self._respond(request, vacancy, status.HTTP_200_OK)


class QuestionsListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (QuestionJSONRenderer,)
    serializer_class = QuestionSerializer
    queryset = Question.objects.select_related("author__user")

    def _get_vacancy(self) -> Vacancy:
        return get_object_or_404(Vacancy, slug=self.kwargs["vacancy_slug"])

    def get_queryset(self) -> QuerySet[Question]:
        return self.queryset.filter(vacancy=self._get_vacancy())

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.serializer_class(
            data=request.data.get("question", {}),
            context={
                "author": request.user.profile,
                "vacancy": self._get_vacancy(),
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestionsDestroyAPIView(generics.DestroyAPIView):
    permission_classes = (IsAuthenticated, IsQuestionAuthorOrVacancyOwner)
    queryset = Question.objects.select_related("vacancy")
    lookup_url_kwarg = "question_pk"

    def get_queryset(self) -> QuerySet[Question]:
        # Вопрос ищется в пределах вакансии из URL — чужой id под другой вакансией даст 404.
        return self.queryset.filter(vacancy__slug=self.kwargs["vacancy_slug"])


class SkillListAPIView(generics.ListAPIView):
    queryset = Skill.objects.all()
    pagination_class = None
    permission_classes = (AllowAny,)
    serializer_class = SkillSerializer

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.serializer_class(self.get_queryset(), many=True)
        return Response({"skills": serializer.data}, status=status.HTTP_200_OK)
