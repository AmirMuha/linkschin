FROM python:3.11-slim

WORKDIR /app

# Install uv (used in pyproject.toml as the package manager)
RUN pip install uv

# Copy dependencies first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
