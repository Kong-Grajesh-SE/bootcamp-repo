#!/bin/bash

# Set Flask environment to production
export FLASK_ENV=production
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
GUNICORN_LOG_LEVEL=${GUNICORN_LOG_LEVEL:-"error"}
PII_SERVICE_ENGINE_CONF=${PII_SERVICE_ENGINE_CONF:-"ai_pii_service/nlp_engine_conf.yml"}
PII_SERVICE_LOG_LEVEL=${LOG_LEVEL:-"error"}


# Build TLS arguments if cert pair is provided
TLS_ARGS=""
BIND_PORT=8080
if [[ -n "$GUNICORN_CERTFILE" && -n "$GUNICORN_KEYFILE" ]]; then
  TLS_ARGS="--certfile $GUNICORN_CERTFILE --keyfile $GUNICORN_KEYFILE"
  BIND_PORT=8443
fi

# Run Gunicorn with error-level logging and dynamic worker count
export PYTHONPATH=$PYTHONPATH:/app/ai_pii_service
poetry run gunicorn -w $GUNICORN_WORKERS -b 0.0.0.0:$BIND_PORT --log-level $GUNICORN_LOG_LEVEL --access-logfile '-' $TLS_ARGS ai_pii_service.server:app
