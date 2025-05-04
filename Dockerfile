# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
# Prevents Python from writing pyc files to disc (equivalent to python -B)
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures Python output is sent straight to terminal without being buffered
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for libraries with C extensions)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code directory into the container at /app/src
COPY src/ ./src/

# Make port 5000 available to the world outside this container (adjust if your Flask app uses a different port)
# The PORT env var will be set by the hosting environment (like Render) or Docker run command
EXPOSE 5000

# Define the command to run the application using Gunicorn
# It looks for the 'app' Flask object within the 'src.bot' module
# The number of workers can be adjusted based on the server resources (using 1 to prevent duplicate bot instances)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "src.bot:app"]