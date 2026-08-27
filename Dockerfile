FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

RUN useradd -m appuser
USER appuser

CMD ["python", "-m", "src.pipeline"]