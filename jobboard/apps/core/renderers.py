from typing import Any

from rest_framework.renderers import JSONRenderer


class JobBoardJSONRenderer(JSONRenderer):
    """Оборачивает ответ в объект с именованным ключом: {"vacancy": {...}} или {"vacancies": [...]}.

    Сериализация идёт через стандартный
    JSONRenderer (UTF-8 без экранирования кириллицы), пустое тело для 204 не ломается.
    """

    charset = "utf-8"
    object_label = "object"
    pagination_object_label = "objects"
    pagination_count_label = "count"

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict[str, Any] | None = None,
    ) -> bytes:
        if data is None:
            return b""

        if isinstance(data, dict) and data.get("errors") is not None:
            payload = data
        elif isinstance(data, dict) and data.get("results") is not None:
            payload = {
                self.pagination_object_label: data["results"],
                self.pagination_count_label: data["count"],
            }
        else:
            payload = {self.object_label: data}

        return super().render(payload, accepted_media_type, renderer_context)
