FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY billing_service ./billing_service
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd --uid 10001 --create-home billing && mkdir -p .local && chown -R billing:billing /app
USER 10001
EXPOSE 8000
CMD ["uvicorn", "billing_service.api:app", "--host", "0.0.0.0", "--port", "8000"]
