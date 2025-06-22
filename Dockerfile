FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY main.py ./
COPY requirements.txt ./
COPY setup.py ./
COPY pyproject.toml ./
COPY slag ./slag/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create comments directory
RUN mkdir -p /app/comments

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
