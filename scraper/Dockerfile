FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/etl
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
# etl/aturan_bersih.py dipasang lewat volume (lihat docker-compose.yml), supaya aturannya sama dengan etl_master.py
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]