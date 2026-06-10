# Kong Konnect Bootcamp

Hands-on labs for Kong Konnect - from API gateway fundamentals to AI-powered agentic workflows. Each module is self-contained with declarative decK files, test commands, and step-by-step walkthroughs.

## Modules

Each module ships with both a **decK CLI** walkthrough and a **Konnect UI**
walkthrough so you can choose your delivery style - both reach the same end
state on the same control plane.

| Module | Description | CLI guide | UI guide |
|--------|-------------|-----------|----------|
| [api-gateway](01-api-gateway/) | Core gateway plugins - rate limiting, caching, auth, CORS, logging, consumer groups - plus Kong Identity (M2M), OIDC with Auth0, and Upstream OAuth | [README](01-api-gateway/README.md) | [README-UI](01-api-gateway/README-UI.md) |
| [apiops](02-apiops/) | decK CLI mastery - sync, diff, validate, dump, lint, OpenAPI-to-Kong, tags, templates | [README](02-apiops/README.md) | [README-UI](02-apiops/README-UI.md) |
| [ai-gateway](04-ai-gateway/) | LLM controls - multi-provider routing, prompt guards, semantic cache, PII sanitization, AI rate limiting, custom guardrails | [README](04-ai-gateway/README.md) | [README-UI](04-ai-gateway/README-UI.md) |
| [mcp-a2a](05-mcp-a2a/) | Agentic AI - MCP passthrough & conversion listeners, multi-team aggregation, OAuth2 PKCE, A2A routing | [README](05-mcp-a2a/README.md) | [README-UI](05-mcp-a2a/README-UI.md) |
| [api-portal](03-api-portal/) | Developer Portal - publish APIs, app registration, self-service credentials | [README](03-api-portal/README.md) | (dual-track: UI walkthrough inline) |

### Stage Demo (optional)

| Folder | Description | Guide |
|---|---|---|
| [bootcamp-automation](bootcamp-automation/) | **AI agent driving the Konnect UI through Kong** - Playwright MCP server gated by `key-auth` + `rate-limiting` + `ai-mcp-proxy`. Showcase that ties every prior module's plugins back together. | [README](bootcamp-automation/README.md) |

### External Identity Provider

This bootcamp uses **[Auth0](https://auth0.com/)** (free tenant) as the
external OpenID Connect / OAuth2 provider. Auth0 is cloud-hosted - no Docker
container to manage. Each module's README explains how to configure the
required Auth0 applications, APIs, and users.

| Service | Used by |
|---|---|
| Auth0 tenant (OIDC / OAuth2) | 01-api-gateway (steps 16-17), 05-mcp-a2a (step 5) |

## Prerequisites

- [Kong Konnect](https://cloud.konghq.com/) account with a serverless control plane
- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- [Auth0](https://auth0.com/) account (free tenant) - external IdP for OIDC/OAuth2 modules
- [Redis Cloud](https://redis.io/cloud/) account (free tier with RediSearch module) - for AI gateway semantic cache
- [ngrok](https://ngrok.com/) - to expose local services to the serverless data plane
- Docker (for modules that run local AI services exposed via ngrok)
- A Konnect Personal Access Token (PAT)

```bash
export KONNECT_TOKEN="<your-konnect-pat>"
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=https://<YOUR_SERVERLESS_PROXY_URL>
```

## Recommended Order

| # | Module | Approx. time | New concepts introduced |
|---|---|---|---|
| 1 | **api-gateway** | 2–3 hrs | Services, routes, plugins, consumers, plugin scopes, Kong Identity (M2M), OIDC (Auth0), token introspection, Upstream OAuth |
| 2 | **apiops** | 2 hrs | `deck gateway` vs `deck file`, partials, tags, OpenAPI→Kong, lint, patch |
| 3 | **ai-gateway** | 2–3 hrs | AI Proxy multi-provider LB, embeddings, semantic cache, prompt/response guards, PII redaction, token rate limiting |
| 4 | **mcp-a2a** | 1.5–2 hrs | MCP protocol, listener modes, OAuth2 + PKCE, A2A agent routing |
| 5 | **api-portal** | 2 hrs | Konnect API Catalog, publications, auth strategies, developer self-service |

Each module's README opens with a "What you bring forward" preamble so you
know which concepts carry through from earlier modules.

## Cleanup Between Bootcamps

Run these steps to reset the environment so the repo is ready for the next
bootcamp session.

### 1. Reset the Konnect Control Plane

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force
```

### 2. Stop and remove Docker services

```bash
# Stop local services (AI gateway backends, MCP servers)
cd 04-ai-gateway && docker compose down -v && cd ..
cd 05-mcp-a2a   && docker compose down -v && cd ..
```

### 3. Clean up Auth0

- Reset Auth0 test users if needed
- Remove test applications created during the bootcamp

### 4. Remove generated files

The AI gateway module generates cumulative state snapshots during
`deck file add-plugins` steps. These are gitignored but accumulate on disk:

```bash
rm -rf 04-ai-gateway/deck/_snapshots/
rm -rf 01-api-gateway/output/
rm -f /tmp/current-state.yaml /tmp/with-plugin.yaml
```

### 5. Reset git working tree (if needed)

```bash
git checkout -- .
git clean -fd
```

## License

This project is licensed under the [MIT License](LICENSE).
