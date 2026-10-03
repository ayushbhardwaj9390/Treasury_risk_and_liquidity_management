FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --uid 10001 --create-home treasury && chown treasury:treasury /app
COPY --chown=treasury:treasury . .
USER treasury
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
