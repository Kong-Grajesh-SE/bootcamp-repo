# Kong Konnect Bootcamp

Hands-on labs for Kong Konnect — from API gateway fundamentals to AI-powered agentic workflows. Each module is self-contained with declarative decK files, test commands, and step-by-step walkthroughs.

## Modules

| Module | Description | Guide |
|--------|-------------|-------|
| [api-gateway](api-gateway/) | Core gateway plugins — rate limiting, caching, auth, CORS, logging, consumer groups | [README](api-gateway/README.md) |
| [ai-gateway](ai-gateway/) | LLM controls — multi-provider routing, prompt guards, semantic cache, PII sanitization, AI rate limiting | [README](ai-gateway/README.md) |
| [mcp-a2a](mcp-a2a/) | Agentic AI — MCP passthrough & conversion listeners, multi-team aggregation, OAuth2 PKCE, A2A routing | [README](mcp-a2a/README.md) |
| [apiops](apiops/) | decK CLI mastery — sync, diff, validate, dump, lint, OpenAPI-to-Kong, tags, templates | [README](apiops/README.md) |
| [api-portal](api-portal/) | Developer Portal — publish APIs, app registration, self-service credentials | [README](api-portal/README.md) |

## Prerequisites

- [Kong Konnect](https://cloud.konghq.com/) account with a control plane
- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- Docker (for modules that run local services)
- A Konnect Personal Access Token (PAT)

```bash
export KONNECT_TOKEN="<your-konnect-pat>"
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=http://localhost:8000   # or your serverless gateway URL
```

## Recommended Order

1. **api-gateway** — Learn core Kong concepts (services, routes, plugins, consumers)
2. **apiops** — Master decK workflows (sync, diff, dump, lint, tags)
3. **ai-gateway** — Add AI/LLM controls on top of gateway fundamentals
4. **mcp-a2a** — Agentic AI patterns (MCP, A2A) with Kong
5. **api-portal** — Publish and manage APIs through the Developer Portal

## License

This project is licensed under the [MIT License](LICENSE).
