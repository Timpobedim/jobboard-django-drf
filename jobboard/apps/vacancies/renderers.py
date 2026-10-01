from jobboard.apps.core.renderers import JobBoardJSONRenderer


class VacancyJSONRenderer(JobBoardJSONRenderer):
    object_label = "vacancy"
    pagination_object_label = "vacancies"
    pagination_count_label = "vacanciesCount"


class QuestionJSONRenderer(JobBoardJSONRenderer):
    object_label = "question"
    pagination_object_label = "questions"
    pagination_count_label = "questionsCount"
