from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from jobboard.apps.authentication.models import User
from jobboard.apps.profiles.models import Profile


@receiver(post_save, sender=User)
def create_related_profile(
    sender: type[User], instance: User, created: bool, **kwargs: Any
) -> None:
    """У каждого пользователя ровно один профиль — создаём его вместе с пользователем."""
    if instance and created:
        Profile.objects.create(user=instance)
