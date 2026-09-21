FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
EXPOSE 8080

# Shell form (not JSON-array form) is required here for ${PORT} substitution; `exec` still
# ensures gunicorn replaces the shell process so it receives container stop signals directly.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 run:app
