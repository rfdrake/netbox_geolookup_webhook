# docker built -t create-webhook-folder .
# docker run -p 5000:5000 --env-file create_folder.env create-webhook-folder
FROM python:3.11.2-slim

# Set the working directory within the container
WORKDIR /app

COPY requirements.txt /app/

RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Expose port 5000 for the Flask application
EXPOSE 5000

# Define the command to run the Flask application using Gunicorn
CMD ["gunicorn", "function:app", "-b", "0.0.0.0:5000", "-w", "4"]
