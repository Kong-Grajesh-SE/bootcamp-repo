# Kong Konnect Bootcamp

Hands-on labs for Kong Konnect - from API gateway fundamentals to AI-powered agentic workflows. Each module is self-contained with declarative decK files, test commands, and step-by-step walkthroughs.

## Modules

Each module ships with both a **decK CLI** walkthrough and a **Konnect UI**
walkthrough so you can choose your delivery style - both reach the same end
state on the same control plane.

| Module | Description | CLI guide | UI guide |
|--------|-------------|-----------|----------|
| [api-gateway](01-api-gateway/) | Core gateway plugins - rate limiting, caching, auth, CORS, logging, consumer groups - plus Kong Identity (M2M), OIDC with Keycloak, and Upstream OAuth | [README](01-api-gateway/README.md) | [README-UI](01-api-gateway/README-UI.md) |
| [apiops](02-apiops/) | decK CLI mastery - sync, diff, validate, dump, lint, OpenAPI-to-Kong, tags, templates | [README](02-apiops/README.md) | [README-UI](02-apiops/README-UI.md) |
| [ai-gateway](04-ai-gateway/) | LLM controls - multi-provider routing, prompt guards, semantic cache, PII sanitization, AI rate limiting, custom guardrails | [README](04-ai-gateway/README.md) | [README-UI](04-ai-gateway/README-UI.md) |
| [mcp-a2a](05-mcp-a2a/) | Agentic AI - MCP passthrough & conversion listeners, multi-team aggregation, OAuth2 PKCE, A2A routing | [README](05-mcp-a2a/README.md) | [README-UI](05-mcp-a2a/README-UI.md) |
| [api-portal](03-api-portal/) | Developer Portal - publish APIs, app registration, self-service credentials | [README](03-api-portal/README.md) | (dual-track: UI walkthrough inline) |

### Stage Demo (optional)

| Folder | Description | Guide |
|---|---|---|
| [bootcamp-automation](bootcamp-automation/) | **AI agent driving the Konnect UI through Kong** - Playwright MCP server gated by `key-auth` + `rate-limiting` + `ai-mcp-proxy`. Showcase that ties every prior module's plugins back together. | [README](bootcamp-automation/README.md) |

### Shared services

| Folder | Description | Used by |
|---|---|---|
| [keycloak](keycloak/) | **One shared Keycloak** (realm `bootcamp`) - external OpenID Connect / OAuth2 provider. Holds every module's clients (`kong`, `kong-m2m`, `mcp-service-client`, `mcp-pkce-client`) and users (`alice`, `bob-admin`, `agent-user`). Start once: `cd keycloak && docker compose up -d`. | 01-api-gateway (steps 16–17), 05-mcp-a2a (step 5) |

## Prerequisites

- [Kong Konnect](https://cloud.konghq.com/) account with a control plane
- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- Docker (for modules that run local services)
- A Konnect Personal Access Token (PAT)

```bash
export KONNECT_TOKEN="<your-konnect-pat>"
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=http://localhost:8000
```

## Recommended Order

| # | Module | Approx. time | New concepts introduced |
|---|---|---|---|
| 1 | **api-gateway** | 2–3 hrs | Services, routes, plugins, consumers, plugin scopes, Kong Identity (M2M), OIDC (Keycloak), token introspection, Upstream OAuth |
| 2 | **apiops** | 2 hrs | `deck gateway` vs `deck file`, partials, tags, OpenAPI→Kong, lint, patch |
| 3 | **ai-gateway** | 2–3 hrs | AI Proxy multi-provider LB, embeddings, semantic cache, prompt/response guards, PII redaction, token rate limiting |
| 4 | **mcp-a2a** | 1.5–2 hrs | MCP protocol, listener modes, OAuth2 + PKCE, A2A agent routing |
| 5 | **api-portal** | 2 hrs | Konnect API Catalog, publications, auth strategies, developer self-service |

Each module's README opens with a "What you bring forward" preamble so you
know which concepts carry through from earlier modules.

## Feedback and Contributions

Found an error, outdated step, or have a suggestion to improve the content?
Please [open an issue](https://github.com/Kong-Grajesh-SE/bootcamp-repo/issues) - all feedback is welcome and appreciated.


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
# Stop all module services
cd 04-ai-gateway && docker compose down -v && cd ..
cd 05-mcp-a2a   && docker compose down -v && cd ..
cd keycloak     && docker compose down -v && cd ..

# Remove the Kong DP container (replace with your container name)
docker rm -f <kong-dp-container>

# Clean up the shared network (only if no other containers use it)
docker network rm kong-net 2>/dev/null || true
```

### 3. Remove generated files

The AI gateway module generates cumulative state snapshots during
`deck file add-plugins` steps. These are gitignored but accumulate on disk:

```bash
rm -rf 04-ai-gateway/deck/_snapshots/
rm -rf 01-api-gateway/output/
rm -f /tmp/current-state.yaml /tmp/with-plugin.yaml
```

### 4. Reset git working tree (if needed)

```bash
git checkout -- .
git clean -fd
```

## License

This project is licensed under the [MIT License](LICENSE).
