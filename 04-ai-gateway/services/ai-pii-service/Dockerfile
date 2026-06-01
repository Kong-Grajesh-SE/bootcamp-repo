# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project into the container
COPY . /app

ARG MODELS="en_core_web_lg"
ARG NLP_ENGINE="spacy"
ARG PRODUCTION="true"
# Install all dependencies and remove them
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    yq \
    && apt-get clean \
    && pip install --upgrade pip \
    && pip install poetry \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && export PATH="/root/.cargo/bin:${PATH}" \
    && poetry config virtualenvs.create false \
    && poetry install && poetry cache clear . --all --no-interaction && rm -rf ~/.cache/pypoetry \
    && apt-get remove --purge -y \
    build-essential \
    curl \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cargo /root/.rustup
RUN if [ "$NLP_ENGINE" = "stanza" ]; then \
        poetry add torch@2.9.1 --source pytorch-cpu-only \
        && poetry add stanza@">=1.10.1,<2.0.0" \
        && poetry cache clear . --all --no-interaction && rm -rf ~/.cache/pypoetry; \
    fi

#Generate nlp_engine_conf.yml
RUN if [ "$PRODUCTION" = "true" ]; then \
        sep="" \
        && yq_eval=".models=[" \
        && for model in $MODELS; do \
        poetry run python -m spacy download $model; \
        lang_code="${model%%_*}"; \
        yq_eval="$yq_eval$sep{\"lang_code\": \"$lang_code\", \"model_name\": \"$model\"}"; \
        sep=", "; \
        done \
        && yq_eval="$yq_eval]" \
        && yq_eval="$yq_eval | .nlp_engine_name=\"$NLP_ENGINE\"" \
        && yq -Yi "${yq_eval}" /app/ai_pii_service/nlp_engine_conf.yml \
        && poetry run tldextract --update; \
    fi

# Expose port 8080 (HTTP) and 8443 (HTTPS) to the outside world
EXPOSE 8080
EXPOSE 8443

ENV GUNICORN_WORKERS=2
ENV GUNICORN_LOG_LEVEL=info
ENV GUNICORN_CERTFILE=""
ENV GUNICORN_KEYFILE=""
ENV PII_SERVICE_ENGINE_CONF=ai_pii_service/nlp_engine_conf.yml

# Ensure the entrypoint script is executable
RUN chmod +x /app/gunicorn_entrypoint.sh

# Use the entrypoint script to run the server
ENTRYPOINT ["/app/gunicorn_entrypoint.sh"]
