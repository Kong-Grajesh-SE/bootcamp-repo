# Use an official nvidia image supporting cuda.
# You can also use slim Python image "python:3.9-slim"
FROM nvidia/cuda:12.9.0-base-ubuntu22.04

# Create a new user and group with non-root privileges
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set the working directory
WORKDIR /app

# Copy the project files
COPY . /app

# Adjust file permissions to allow the non-root user to read/write
RUN chown -R appuser:appgroup /app

# Install Python, pip, and system dependencies
# For python image remove python3 and python3-pip
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Poetry and Gunicorn
RUN python3 -m pip install --upgrade --no-cache-dir pip setuptools wheel poetry

# Prevent Poetry from creating a virtual environment
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --no-interaction --no-ansi

# Preload encodings for tiktoken
ENV TIKTOKEN_CACHE_DIR=/app/tiktoken_cache
RUN mkdir ${TIKTOKEN_CACHE_DIR}
RUN python3 /app/scripts/preload.py

# Clean up unnecessary packages and cache
RUN apt-get remove --purge -y \
    python3-pip python3-setuptools python3-wheel \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV GUNICORN_WORKERS=2
ENV GUNICORN_LOG_LEVEL=info
ENV LLMLINGUA_LOG_LEVEL=info
ENV LLMLINGUA_MODEL_NAME="microsoft/llmlingua-2-xlm-roberta-large-meetingbank"

# Switch to the non-root user
USER appuser

# Ensure the entrypoint script is executable
RUN chmod +x /app/gunicorn_entrypoint.sh

# Expose the app port
EXPOSE 8080

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f -X POST http://localhost:8080 \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":36,"method":"llm.v1.compressPrompt","params":{"text":[{"text":"text to initialise the compressor","msg_id":2}],"advanced_logging":false,"compression_ranges":[{"min_tokens":0,"max_tokens":10000,"value":0.5}],"model_name":"gpt-4o-mini","compressor_type":"rate"}}' || exit 1

# Launch the app using Gunicorn
ENTRYPOINT ["/app/gunicorn_entrypoint.sh"]

