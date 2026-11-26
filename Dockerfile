FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a normal user, not root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# gunicorn = production web server. PORT is set by Render; default 8000 in Docker.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} app:app"]
