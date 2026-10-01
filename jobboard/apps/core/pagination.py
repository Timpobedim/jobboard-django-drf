from rest_framework.pagination import LimitOffsetPagination as DRFLimitOffsetPagination


class LimitOffsetPagination(DRFLimitOffsetPagination):
    """?limit=&offset= как в спецификации RealWorld, но с верхней границей размера страницы."""

    default_limit = 20
    max_limit = 100
