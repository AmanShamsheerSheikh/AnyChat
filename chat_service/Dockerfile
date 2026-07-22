FROM python:3.11-slim

WORKDIR /app
COPY chat_service/ ./chat_service/
RUN pip install --no-cache-dir -r chat_service/requirements.txt
WORKDIR /app/chat_service
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]