FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt api/requirements-dev.txt ./api/
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api ./api
COPY data ./data
COPY docs ./docs

ENV PYTHONPATH=/app/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
