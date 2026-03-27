FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY generators/ generators/
COPY api/ api/
COPY __init__.py .

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
