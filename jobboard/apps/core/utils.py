import secrets
import string

DEFAULT_CHAR_STRING = string.ascii_lowercase + string.digits


def generate_random_string(chars: str = DEFAULT_CHAR_STRING, size: int = 6) -> str:
    """Случайный суффикс для slug. secrets вместо random: суффикс нельзя предсказать."""
    return "".join(secrets.choice(chars) for _ in range(size))
