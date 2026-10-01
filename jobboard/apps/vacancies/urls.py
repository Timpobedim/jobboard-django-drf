from django.urls import include, path
from rest_framework.routers import DefaultRouter

from jobboard.apps.vacancies.views import (
    QuestionsDestroyAPIView,
    QuestionsListCreateAPIView,
    SkillListAPIView,
    VacancyFeedAPIView,
    VacancySaveAPIView,
    VacancyViewSet,
)

app_name = "vacancies"

router = DefaultRouter(trailing_slash=False)
router.register("vacancies", VacancyViewSet, basename="vacancy")

urlpatterns = [
    # «vacancies/feed» объявлен до роутера, иначе «feed» будет принят за slug вакансии.
    path("vacancies/feed", VacancyFeedAPIView.as_view(), name="feed"),
    path("vacancies/<slug:vacancy_slug>/save", VacancySaveAPIView.as_view(), name="save"),
    path(
        "vacancies/<slug:vacancy_slug>/questions",
        QuestionsListCreateAPIView.as_view(),
        name="questions",
    ),
    path(
        "vacancies/<slug:vacancy_slug>/questions/<int:question_pk>",
        QuestionsDestroyAPIView.as_view(),
        name="question-detail",
    ),
    path("skills", SkillListAPIView.as_view(), name="skills"),
    path("", include(router.urls)),
]
