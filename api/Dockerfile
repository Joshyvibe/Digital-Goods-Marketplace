FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

# Static files are baked into the image (served by WhiteNoise); the throwaway key only exists
# so settings can load during the build.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && useradd -m -u 10001 app && chown -R app /app

USER app

EXPOSE 8000

# Migrations run on every boot rather than as a separate release step — simplest correct
# option for a single-instance deploy; revisit if this ever runs with >1 web replica
# (concurrent migrate runs racing) or needs a real release-phase hook.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --timeout 60 --access-logfile -"]
