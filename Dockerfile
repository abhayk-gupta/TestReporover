# 1. Use an official Python base image (matching your venv)
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install system dependencies
# (We need poppler-utils for the PyPDFLoader to work)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy and install Python requirements
# This is done in a separate step to leverage Docker's build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
# (This copies src/ and app/)
COPY . .

# No CMD or ENTRYPOINT, as this will be provided by docker-compose