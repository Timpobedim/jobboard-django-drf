from django.contrib import admin

from jobboard.apps.vacancies.models import Question, Skill, Vacancy


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "city", "remote", "experience", "created_at")
    list_filter = ("remote", "experience")
    search_fields = ("title", "description")


admin.site.register(Skill)
admin.site.register(Question)
