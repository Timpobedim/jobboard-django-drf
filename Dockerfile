FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv==0.12.13 \
    && uv pip install --system --no-cache -r pyproject.toml

COPY manage.py ./
COPY jobboard ./jobboard

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn jobboard.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
