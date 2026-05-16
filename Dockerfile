FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# AIRFLOW_URL intentionally has NO default — absence triggers --demo mode

WORKDIR /app

COPY pyproject.toml README.md ./
COPY terminair ./terminair
COPY docs ./docs

RUN pip install --no-cache-dir -e .

VOLUME ["/app/target"]

CMD if [ -n "$AIRFLOW_URL" ] && [ "$TERMINAIR_DEMO" != "1" ]; then \
      exec python -m terminair \
        --url "$AIRFLOW_URL" \
        ${TERMINAIR_USER:+--user "$TERMINAIR_USER"} \
        ${TERMINAIR_PASSWORD:+--password "$TERMINAIR_PASSWORD"}; \
    else \
      exec python -m terminair --demo; \
    fi
