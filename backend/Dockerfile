FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "set -e; python manage.py migrate --noinput; python manage.py seed_demo; python manage.py collectstatic --noinput; gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2"]
