# Use an official lightweight Python base image
FROM python:3.13-alpine

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY ./src .

# Run your script (replace script.py with your filename)
CMD ["python", "-u", "main.py"]
