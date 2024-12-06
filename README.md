#Check Api Health

This project implements a Health Check RESTful API using Python, FastAPI, MySQL, and SQLAlchemy. The `/healthz` endpoint checks if the application is connected to the database and returns appropriate HTTP status codes. The project is designed for cloud-native architecture and tested locally using Postman.

## Features
- Health check endpoint: `/healthz`
- Returns HTTP 200 OK if the service is healthy
- Returns HTTP 503 Service Unavailable if the database connection fails
- Only allows HTTP GET requests (returns 405 Method Not Allowed for others)
- No payload allowed in requests (returns 400 Bad Request if present)
- No caching of the API response

## Prerequisites

- **Python 3.x** installed
- **MySQL** installed and running
- **Visual Studio Code** (or any other code editor)
- **Postman** for API testing

Python dependencies:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `mysql-connector-python`
- `python-dotenv`

Install dependencies using the following command:

```bash
pip install -r requirements.txt

# updated changes for assignment09 submission