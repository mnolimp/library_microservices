FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./proto /app/proto

CMD sh -c "python app/grpc_server.py & uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"