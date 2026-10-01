from typing import Any

from django.db import transaction
from rest_framework import serializers

from jobboard.apps.profiles.serializers import ProfileSerializer
from jobboard.apps.vacancies.models import Question, Skill, Vacancy
from jobboard.apps.vacancies.relations import SkillRelatedField


def get_or_create_skills(names: list[str]) -> list[Skill]:
    return [Skill.objects.get_or_create(name=name)[0] for name in names]


class VacancySerializer(serializers.ModelSerializer):
    company = ProfileSerializer(read_only=True)
    slug = serializers.SlugField(read_only=True)
    description = serializers.CharField(max_length=500)
    salaryFrom = serializers.IntegerField(
        source="salary_from",
        required=False,
        allow_null=True,
        min_value=0,
    )
    salaryTo = serializers.IntegerField(
        source="salary_to",
        required=False,
        allow_null=True,
        min_value=0,
    )
    skillList = SkillRelatedField(source="skills", required=False)
    saved = serializers.SerializerMethodField()
    savedCount = serializers.SerializerMethodField(method_name="get_saved_count")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Vacancy
        fields = (
            "slug",
            "title",
            "description",
            "body",
            "salaryFrom",
            "salaryTo",
            "city",
            "remote",
            "experience",
            "skillList",
            "company",
            "saved",
            "savedCount",
            "createdAt",
            "updatedAt",
        )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        salary_from = attrs.get("salary_from", getattr(self.instance, "salary_from", None))
        salary_to = attrs.get("salary_to", getattr(self.instance, "salary_to", None))

        if salary_from is not None and salary_to is not None and salary_from > salary_to:
            raise serializers.ValidationError(
                {"salaryFrom": "Нижняя граница зарплаты больше верхней."},
            )

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Vacancy:
        skill_names: list[str] = validated_data.pop("skills", [])

        with transaction.atomic():
            vacancy = Vacancy.objects.create(company=self.context["company"], **validated_data)
            vacancy.skills.set(get_or_create_skills(skill_names))

        return vacancy

    def update(self, instance: Vacancy, validated_data: dict[str, Any]) -> Vacancy:
        skill_names: list[str] | None = validated_data.pop("skills", None)

        with transaction.atomic():
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.save()

            if skill_names is not None:
                instance.skills.set(get_or_create_skills(skill_names))

        return instance

    def get_saved(self, instance: Vacancy) -> bool:
        annotated = getattr(instance, "is_saved", None)
        if annotated is not None:
            return bool(annotated)

        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False

        return bool(request.user.profile.has_saved(instance))

    def get_saved_count(self, instance: Vacancy) -> int:
        annotated = getattr(instance, "saved_count", None)
        if annotated is not None:
            return int(annotated)

        return int(instance.saved_by.count())

    def to_representation(self, instance: Vacancy) -> dict[str, Any]:
        # Флаг подписки на компанию уже посчитан в аннотации запроса — передаём его профилю.
        followed = getattr(instance, "company_followed", None)
        if followed is not None:
            instance.company.is_followed = followed  # type: ignore[attr-defined]

        data: dict[str, Any] = super().to_representation(instance)
        return data


class QuestionSerializer(serializers.ModelSerializer):
    author = ProfileSerializer(read_only=True)
    body = serializers.CharField(max_length=2000)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Question
        fields = ("id", "author", "body", "createdAt", "updatedAt")

    def create(self, validated_data: dict[str, Any]) -> Question:
        return Question.objects.create(
            vacancy=self.context["vacancy"],
            author=self.context["author"],
            **validated_data,
        )


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("name",)

    def to_representation(self, instance: Skill) -> str:  # type: ignore[override]
        return instance.name
