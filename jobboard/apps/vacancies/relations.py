from typing import Any

from django.db.models import Manager
from rest_framework import serializers

MAX_SKILLS = 15
MAX_SKILL_LENGTH = 40


class SkillRelatedField(serializers.Field):
    """Список навыков вакансии в JSON: "skillList": ["python", "sql"].

    Поле только нормализует названия (не создаёт навыки во время валидации),
    а навыки создаются в сериализаторе внутри транзакции.
    """

    def to_representation(self, value: Manager[Any]) -> list[str]:
        return sorted(skill.name for skill in value.all())

    def to_internal_value(self, data: Any) -> list[str]:
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            raise serializers.ValidationError("Ожидается список строк.")

        names: list[str] = []
        for item in data:
            name = item.strip().lower()[:MAX_SKILL_LENGTH]
            if name and name not in names:
                names.append(name)

        if len(names) > MAX_SKILLS:
            raise serializers.ValidationError(f"Не больше {MAX_SKILLS} навыков.")

        return names
