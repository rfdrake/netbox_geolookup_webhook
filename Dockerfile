# docker build -t netbox-geolookup-webhook .
# docker run -p 5000:5000 --env-file geolookup.env netbox-geolookup-webhook
FROM python:3-slim

# Set the working directory within the container
WORKDIR /app

COPY requirements.txt /app/

RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Expose port 5000 for the Flask application
EXPOSE 5000

# Define the command to run the Flask application using Gunicorn
# Important:  -w 1 is REQUIRED so we don't send too many queries to nominatim
CMD ["gunicorn", "function:app", "-b", "0.0.0.0:5000", "-w", "1"]
