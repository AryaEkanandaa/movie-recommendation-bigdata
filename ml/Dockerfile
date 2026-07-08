FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/ml

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        curl \
        default-jdk-headless \
        procps \
    && rm -rf /var/lib/apt/lists/*

COPY ml/requirements.txt /tmp/requirements.txt
COPY ml/requirements_pyspark_modelling.txt /tmp/requirements_pyspark_modelling.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements_pyspark_modelling.txt
