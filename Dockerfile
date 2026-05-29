FROM python:3.11-slim

WORKDIR /app

COPY gever_management/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gever_management/ .

EXPOSE 8000

CMD ["python", "main.py", "api"]
