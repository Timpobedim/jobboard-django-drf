from typing import Any

from django.http import Http404
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import exception_handler


def core_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Приводит все ошибки API к единому формату {"errors": {...}}.

    Формат одинаков для любой ошибки DRF, включая авторизацию и права, а «не найдено» распознаётся
    через isinstance — в том числе для наследников NotFound.
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, NotFound | Http404):
        return _handle_not_found_error(context, response)

    return _handle_generic_error(response)


def _handle_generic_error(response: Response) -> Response:
    response.data = {"errors": response.data}
    return response


def _handle_not_found_error(context: dict[str, Any], response: Response) -> Response:
    view = context.get("view")
    queryset = getattr(view, "queryset", None)

    if queryset is not None:
        error_key = queryset.model._meta.model_name
        response.data = {"errors": {error_key: response.data["detail"]}}
        return response

    return _handle_generic_error(response)
