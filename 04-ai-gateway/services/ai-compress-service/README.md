# AI Prompt Compression Service

This HTTP API compresses LLM prompts to reduce token usage using [LLMLingua 2](https://github.com/microsoft/LLMLingua). It supports both direct HTTP and JSON-RPC calls, and integrates well with Kong Gateway via plugin.

> ✅ **Kong plugin available:** https://github.com/KongHQ-CX/ai-prompt-compressor


![Alt text](/ai-prompt-compressor-logo.svg)

---

## 🚀 Endpoints

- `POST /llm/v1/compressPrompt`: Compress prompts based on token rate or target token count.
- `GET /status`: Returns current model and device status.
- `POST /`: JSON-RPC endpoint supporting the `llm.v1.compressPrompt` method.

---

## 🧰 Getting Started

### ➤ Run with Poetry (standalone)

First install dependencies via [Poetry](https://python-poetry.org/):

```sh
poetry install
```

Run the server:

```sh
poetry run python -m ai_compress_service.server --llmlingua_model_name "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"   --llmlingua_device_map "cpu"
```

### ➤ Run with Python directly

```sh
python server.py --llmlingua_model_name microsoft/llmlingua-2-xlm-roberta-large-meetingbank --llmlingua_device_map cpu --port 8080
```

---

## 🐳 Docker

### Build:

You can run with Docker by building the image:

```sh
docker build --platform linux/amd64 -t kong-compressor .
```

### Run:

And then running the container (the following example exposes the service on port `9000`):

```sh
docker run -d --name kong-compressor -p 9000:8080 kong-compressor:arm
```

### Run with GPU:

If you host support NVIDIA drivers, you can run the container with GPU support:

```sh
docker run -d --runtime=nvidia --gpus all --name kong-compressor   -p 9000:8080   -e LLMLINGUA_MODEL_NAME="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"   -e LLMLINGUA_DEVICE_MAP="cuda"   kong-compressor
```

### Tag & Push:

```sh
docker tag kong-compressor:latest yourrepo/kong-compressor:amd
docker push yourrepo/kong-compressor:amd
```

---

## 🔧 Environment Variables

| Variable               | Description                                           | Default                                                       |
|------------------------|-------------------------------------------------------|---------------------------------------------------------------|
| `LLMLINGUA_MODEL_NAME` | LLM Lingua 2 model to use                             | `microsoft/llmlingua-2-xlm-roberta-large-meetingbank`        |
| `LLMLINGUA_DEVICE_MAP` | Device to use (`cpu`, `cuda`, `auto`, `mps`, ...)    | `cpu`                                                         |
| `LLMLINGUA_LOG_LEVEL`  | Log level for compression logic                       | `info`                                                        |
| `GUNICORN_WORKERS`     | Gunicorn process count (for Docker only)             | `2`                                                           |
| `GUNICORN_LOG_LEVEL`   | Log level for Gunicorn (for Docker only)             | `info`                                                        |


So you can for instance run the container:

```sh
$ docker run -d --name kong-compressor -p 9000:8080 -e GUNICORN_WORKERS=2 -e GUNICORN_LOG_LEVEL=info -e LLMLINGUA_LOG_LEVEL=info -e LLMLINGUA_MODEL_NAME='microsoft/llmlingua-2-xlm-roberta-large-meetingbank' kong-compressor -e LLMLINGUA_DEVICE_MAP=auto
```

**Note**: The Docker distribution includes settings that are more suitable for production use, including using Gunicorn as the ingress server to run the underlying Flask application.

---

## 📬 Example Requests

### Basic HTTP

```bash
curl -X POST http://localhost:8080/llm/v1/compressPrompt   -H "Content-Type: application/json"   -d '{
    "text": "Hi, this is a long text with redundant and important parts we want to compress down.",
    "compressor_type": "rate",
    "compression_ranges": [
      { "min_tokens": 0, "max_tokens": 10, "value": 0.8 },
      { "min_tokens": 10, "max_tokens": 100, "value": 0.3 }
    ],
    "model_name": "gpt-4"
  }'
```

Response:
```json
{
    "text": [
        {
            "compress_prompt": "text redundant compress.",
            "compressor_results": {
                "msg_id": 1,
                "original_token_count": 17,
                "compress_token_count": 4,
                "save_token_count": 13,
                "compress_value": 0.3,
                "compress_type": "rate",
                "compressor_model": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
                "information": "Compression was performed and saved 13 tokens"
            },
            "msg_id": 1
        }
    ],
    "duration": 3899
}
```

### JSON-RPC

```bash
curl -X POST http://localhost:8080/   -H "Content-Type: application/json"   -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "llm.v1.compressPrompt",
    "params": {
      "text": [
        { "msg_id": 1, "text": "Hi this is a long message..." },
        { "msg_id": 2, "text": "<LLMLINGUA>This context will be compressed</LLMLINGUA>" }
      ],
      "compressor_type": "rate",
      "compression_ranges": [
        { "min_tokens": 0, "max_tokens": 50, "value": 0.7 },
        { "min_tokens": 50, "max_tokens": 100, "value": 0.3 }
      ],
      "model_name": "gpt-4"
    }
  }'
```

Response:
```json
{
    "jsonrpc": "2.0",
    "result": {
        "text": [
            {
                "compress_prompt": "this long message.",
                "compressor_results": {
                    "msg_id": 1,
                    "original_token_count": 7,
                    "compress_token_count": 4,
                    "save_token_count": 3,
                    "compress_value": 0.7,
                    "compress_type": "rate",
                    "compressor_model": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
                    "information": "Compression was performed and saved 3 tokens"
                },
                "msg_id": 1
            },
            {
                "compress_prompt": "This context compressed",
                "compressor_results": {
                    "msg_id": 2,
                    "original_token_count": 5,
                    "compress_token_count": 3,
                    "save_token_count": 2,
                    "compress_value": 0.7,
                    "compress_type": "rate",
                    "compressor_model": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
                    "information": "Compression was performed and saved 2 tokens"
                },
                "msg_id": 2
            }
        ],
        "duration": 1130
    },
    "id": 1
}
```

---

## ✨ Features

The compression will be standard token compression after stripping polite words. 

However is passing a prompt with context, the compression will compress the context part and only remove polite words for user questions.

- **Smart range-based compression**: Define custom `compression_ranges` for different input sizes.
- **Dual compression strategies**:
  - `rate`: compress to a percentage (e.g., 0.5 = 50%)
  - `target_token`: compress to a fixed token count
- **Token-aware skipping**: No compression if text falls outside defined compression ranges. For target_token, No compression if text tokens lower than target value.
- **Tag-based compression**: Use `<LLMLINGUA> ... </LLMLINGUA>` to target parts of the prompt. This is useful for example to compress a prompt with a context.
- **Politeness stripping**: Common polite expressions are removed before compression (English only).

---

## RAG
This plugin is great to use in cooperation with the Kong "AI Rag Injector" plugin.
The RAG context could be easily compressed by setting the "Inject Template" field with: 
<LLMLINGUA><CONTEXT></LLMLINGUA> | <PROMPT>

---

## 🧪 Running Tests

Execute the following command:

```sh
poetry run pytest tests/test_server.py
poetry run pytest tests/test_api.py
```

---

## 🏗 Production Best Practices

To ensure high performance and reliability in production environments, follow these best practices:

### ✅ Co-locate the Compression Service with Kong Gateway

- Deploy the compression service as close as possible to the Kong Gateway to minimize latency.
- If running on Docker, place both Kong and the compressor service in the same Docker network to allow fast, internal communication.
- If using Kubernetes, deploy them in the same namespace or node pool if possible.

### ⚡ Use GPU Acceleration

LLMLingua models benefit significantly from GPU acceleration, especially for high-throughput environments.

- **Why GPU?** Compression tasks are model-inference-heavy. Using a GPU (e.g., with CUDA) can improve throughput by **5–10x** over CPU-only execution.
- Set the environment variable accordingly:  
  `LLMLINGUA_DEVICE_MAP=cuda`

### ☁️ AWS Deployment Guide

If using AWS, here’s how to quickly spin up a GPU-ready instance:

#### Recommended AMI:

- **AMI Name:** `Deep Learning Base GPU Image (Ubuntu 24.04)`
- **Search in EC2 Console**: Look for **"Deep Learning Base NVIDIA Driver GPU AMI"** under AWS Marketplace.
- **Built-in drivers**: These AMIs include CUDA and NVIDIA drivers pre-installed, reducing setup time.

#### Recommended Instance Types:

| Instance Type  | GPU Model         | vCPUs | RAM  | Ideal For                   |
|----------------|-------------------|-------|------|-----------------------------|
| `g4dn.xlarge`  | NVIDIA T4         | 4     | 16GB | Lightweight real-time loads |
| `g5.xlarge`    | NVIDIA A10G       | 4     | 16GB | Heavier compression jobs    |
| `p3.2xlarge`   | NVIDIA V100       | 8     | 61GB | High-performance batching   |

#### Verifying Driver Installation:

Once the instance is running:

```sh
nvidia-smi
```

Expected output includes GPU name, driver version, and usage statistics.


---

## 📜 Logging

The compression service logs detailed metrics under the `ai.compressor` key in Kong logs (or your custom logging pipeline if integrated independently). These logs help trace, debug, and optimize compression activity.


## 🧾 Log Schema

```json
"ai": {
  "compressor": {
    "duration": 179,
    "compress_items": [
      {
        "msg_id": 2,
        "original_token_count": 10,
        "compress_token_count": 0,
        "save_token_count": 0,
        "information": "No compression was applied because the prompt is too short or its token count falls outside the defined compression ranges."
      },
      {
        "msg_id": 3,
        "compressor_model": "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        "compress_type": "rate",
        "compress_value": 0.8,
        "original_token_count": 21,
        "compress_token_count": 16,
        "save_token_count": 5,
        "information": "Compression was performed and saved 5 tokens"
      }
    ]
  }
}
```

## 🔍 Fields Explained

Top-level
- `duration`: Total time in milliseconds to process all prompt compressions.

*Each* `compress_item`:

| Field                  | Type   | Description                                                                 |
| ---------------------- | ------ | --------------------------------------------------------------------------- |
| `msg_id`               | int    | Identifier for the original input message                                   |
| `original_token_count` | int    | Number of tokens before compression                                         |
| `compress_token_count` | int    | Number of tokens after compression                                          |
| `save_token_count`     | int    | Difference in token count (saved tokens)                                    |
| `compress_type`        | string | `"rate"` or `"target_token"` – type of compression used                     |
| `compress_value`       | number | Rate (e.g. `0.3`) or target token count (e.g. `100`)                        |
| `compressor_model`     | string | Name of the LLMLingua model used                                            |
| `information`          | string | Status message indicating whether compression was applied and effectiveness |

> **Note**: `compress_type`, `compress_value`, and `compressor_model` are included only when compression is applied.

## 🧪 Advanced Logging

If `advanced_logging`=true is passed in the request, additional fields are included:
- `original_text`: Raw input before stripping and compression
- `compress_text`: Final compressed output (pre-tokenization)

These help diagnose issues and visualize compression effectiveness during development or debugging.

## 🧪 Developer Workflow

If you're a developer making changes to the service, follow these steps:

1. Clone the repository to your local machine.
2. Create a new branch for your changes.
3. Commit and push your changes to the new branch.
4. Open a pull request (PR) against the `main` branch.
5. The PR can be merged once all tests and checks pass.

---

## 🚀 Release Process

To publish a new version of the service, follow these steps:

1. Create a new Git tag that follows [Semantic Versioning](https://semver.org/) - format: `v*.*.*`.
   - Example: `v1.2.0`
2. Push the tag to the remote repository.
3. This will trigger the release pipeline, which:
   - Builds the Docker image.
   - Pushes the image to the following registries:
     - **Docker Hub**: [kong/ai-compress-service](https://hub.docker.com/repository/docker/kong/ai-compress-service)
     - **Cloudsmith**: [kong/ai-compress](https://cloudsmith.io/~kong/repos/ai-compress/)

**Important**: Ensure tags are following correct semantic versioning or the release pipeline will not start.

> ✅ Make sure tests pass before tagging a release. Only tagged versions are published.



---

## 📄 License

This is a proprietary application. See [LICENSE](https://github.com/Kong/ai-pii-service/blob/main/LICENSE) for details.

