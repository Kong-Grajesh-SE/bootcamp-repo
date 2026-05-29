#!/bin/bash

# Set Flask environment to production
export FLASK_ENV=production
export TIKTOKEN_CACHE_DIR=/app/tiktoken_cache

# Define defaults
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
GUNICORN_LOG_LEVEL=${GUNICORN_LOG_LEVEL:-"info"}
LLMLINGUA_LOG_LEVEL=${LLMLINGUA_LOG_LEVEL:-"info"}
LLMLINGUA_MODEL_NAME=${LLMLINGUA_MODEL_NAME:-"microsoft/llmlingua-2-xlm-roberta-large-meetingbank"}

# Set Python path
export PYTHONPATH=$PYTHONPATH:/app/ai_compress_service

# Launch Gunicorn
exec gunicorn -w $GUNICORN_WORKERS -b 0.0.0.0:8080 \
  --log-level $GUNICORN_LOG_LEVEL \
  --access-logfile '-' \
  ai_compress_service.server:app
