FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir requests

COPY snow_permission_test.py .

ENTRYPOINT ["python3", "snow_permission_test.py"]
