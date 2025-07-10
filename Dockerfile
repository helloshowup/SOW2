# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# --- Build Optimization ---
# Copy only the requirements file first to take advantage of Docker's layer caching.
# The dependencies will only be re-installed if the requirements.txt file changes.
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --- Application Code ---
# Now, copy the rest of your application code, including the 'app' and 'dev-research' directories.
COPY . .

# No CMD is needed here.
# The command to run the application (e.g., uvicorn for the api or rq for the worker)
# is specified in the "Start Command" field for each service on Render.
