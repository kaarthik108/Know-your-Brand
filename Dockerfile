FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app

COPY . .

USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"

ENV PORT=8080
ENV HOST=0.0.0.0

CMD uvicorn main:app --host ${HOST} --port ${PORT}