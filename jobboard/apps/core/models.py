from django.db import models


class TimestampedModel(models.Model):
    """Абстрактная модель с метками создания и изменения."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at", "-id"]
