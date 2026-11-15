FROM python:3.12-slim

WORKDIR /app

COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY searchengine/ ./searchengine/

RUN groupadd --system --gid 999 app && useradd --system --uid 999 --gid app --no-create-home app \
    && mkdir -p /data && chown app:app /data

ENV SEARCH_DB=/data/search.db \
    SCHEMA_DB=/data/schemas.db \
    PYTHONDONTWRITEBYTECODE=1

VOLUME /data

USER app

EXPOSE 8000

CMD ["uvicorn", "searchengine.server:app", "--host", "0.0.0.0", "--port", "8000"]
