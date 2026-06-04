FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create directories for persistent data
RUN mkdir -p /app/data /app/backup

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backend/app.py
ENV DATA_DIR=/app/data
ENV BACKUP_DIR=/app/backup

EXPOSE 5000

# Use gunicorn for production deployment
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "backend.app:app"]