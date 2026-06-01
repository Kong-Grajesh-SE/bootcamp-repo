# Kong AI Gateway Bootcamp

> Enterprise-grade LLM controls — multi-provider load balancing, prompt engineering, guards, cache, compression, rate limits, PII protection, and semantic AI filters on Konnect.

## Choose Your Guide

| Guide | Focus | Best For |
|-------|-------|----------|
| [README-DECK.md](README-DECK.md) | Declarative (decK CLI) | GitOps, repeatable deploys, CI/CD |
| [README-UI.md](README-UI.md) | Konnect UI (point-and-click) | Live demos, customer walkthroughs |

Both guides configure the **same plugin chain** on the **same control plane**. Pick one path or switch between them.

## File Structure

```
ai-gateway/
├── deck/                               ← 10 incremental decK state files
│   ├── 01-ai-proxy-advanced.yaml       ← AI Proxy + Multi-Provider LB (Mistral + Cerebras)
│   ├── 02-prompt-decorator.yaml        ← + System prompt injection
│   ├── 03-prompt-guard.yaml            ← + Prompt injection blocking (regex)
│   ├── 04-semantic-cache.yaml          ← + Redis vector cache
│   ├── 05-prompt-template.yaml         ← + Named prompt templates
│   ├── 06-ai-sanitizer.yaml            ← + PII redaction
│   ├── 07-prompt-compressor.yaml       ← + Token compression
│   ├── 08-ai-rate-limiting.yaml        ← + Token-aware rate limits (per-model)
│   ├── 09-semantic-prompt-guard.yaml   ← + Semantic prompt guard (embeddings)
│   └── 10-semantic-response-guard.yaml ← + Semantic response guard
├── services/
│   ├── ai-pii-service/                 ← PII Anonymizer (local build)
│   └── ai-compress-service/            ← Prompt Compressor (local build)
├── insomnia/
│   └── kong-ai-gateway-bootcamp.json   ← Insomnia collection (positive + negative tests)
├── docker-compose.yml                  ← Redis Stack + PII + Compressor
├── README.md                           ← This file (index)
├── README-DECK.md                      ← decK walkthrough
└── README-UI.md                        ← Konnect UI walkthrough
```

## Plugin Chain (build order vs runtime order)

This bootcamp adds plugins in the order **01 → 10**: that's the *teaching*
order. Kong doesn't execute plugins in the order you added them — it runs
them by **phase** (access / response / log) and within a phase by each
plugin's built-in priority. You don't configure priorities here; Kong does.

The runtime order you actually get on the request path:

```
Request
  ├─ ai-prompt-template       (rewrite named templates)        ← Step 05
  ├─ ai-prompt-decorator      (inject system prompt)           ← Step 02
  ├─ ai-prompt-guard          (regex deny / allow)             ← Step 03
  ├─ ai-semantic-prompt-guard (embedding-based deny / allow)   ← Step 09
  ├─ ai-sanitizer             (PII redaction, request side)    ← Step 06
  ├─ ai-semantic-cache        (hit → return cached, skip LLM)  ← Step 04
  ├─ ai-prompt-compressor     (token reduction)                ← Step 07
  ├─ ai-rate-limiting-advanced(token budget check)             ← Step 08
  └─ ai-proxy-advanced        (round-robin Mistral ↔ Cerebras) ← Step 01
                                       │
                                       ▼  Provider response
  ├─ ai-semantic-response-guard (block outputs by topic)       ← Step 10
  └─ ai-sanitizer               (PII redaction, response side) ← Step 06
                                       │
                                       ▼
Client
```

Mental model: **the lab teaches plugins one at a time, but at runtime they're
already chained in this order — so each step you add slots into the chain
wherever its priority belongs.** If a later test surprises you, check this
diagram first.

## AI Providers

| Provider | Model | Role |
|----------|-------|------|
| **Mistral** | `mistral-tiny` | Primary chat model |
| **Cerebras** | `gpt-oss-120b` | Secondary chat model (round-robin) |
| **Mistral** | `mistral-embed` | Embeddings (semantic cache, guards) |

Multi-provider load balancing is configured from **Step 01** and carried through every subsequent step.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Kong Gateway 3.14+ / Konnect | Gateway runtime + Control Plane | [cloud.konghq.com](https://cloud.konghq.com) |
| Docker Desktop | Run Redis, PII service, Compress service | [docker.com](https://www.docker.com/get-started) |
| decK CLI | Declarative Kong config | `brew install kong/deck/deck` |
| curl + jq | API testing | Pre-installed on macOS |
| Insomnia | GUI API testing | [insomnia.rest](https://insomnia.rest/) |

## AI Provider Keys

```bash
# Mistral — primary model + embeddings (all steps)
export MISTRAL_API_KEY="<your-mistral-api-key>"
export DECK_MISTRAL_API_KEY="$MISTRAL_API_KEY"

# Cerebras — secondary model for load balancing (all steps)
export CEREBRAS_API_KEY="<your-cerebras-api-key>"
export DECK_CEREBRAS_API_KEY="$CEREBRAS_API_KEY"
```

Verify your keys:

```bash
# Mistral
curl -s https://api.mistral.ai/v1/models \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  | jq '.data[] | select(.id == "mistral-tiny" or .id == "mistral-embed") | .id'

# Cerebras
curl -s https://api.cerebras.ai/v1/models \
  -H "Authorization: Bearer $CEREBRAS_API_KEY" | jq '.data[].id' | head -5
```

## Quick Start

```bash
# 1. Create Docker network (if not exists)
docker network create kong-net 2>/dev/null || true

# 2. Start supporting services
cd ai-gateway
docker compose up -d

# 3. Follow either README-DECK.md or README-UI.md
```

## Reference Links

- [AI Gateway Overview](https://developer.konghq.com/ai-gateway/)
- [ai-proxy-advanced Plugin](https://developer.konghq.com/plugins/ai-proxy-advanced/)
- [AI Plugins Hub](https://developer.konghq.com/plugins/?category=ai)
- [Full Learning Path](https://kong-grajesh-se.github.io/learn-kong-ai-gateway/)
