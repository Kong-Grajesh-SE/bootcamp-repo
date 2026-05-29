# Agentic AI Bootcamp — MCP & A2A with Kong Gateway

> Enterprise-grade MCP proxying, multi-team tool aggregation, OAuth2 PKCE, and A2A agent routing on Konnect.

## Choose Your Guide

| Guide | Focus | Best For |
|-------|-------|----------|
| [README-DECK.md](README-DECK.md) | Declarative (decK CLI) | GitOps, repeatable deploys, CI/CD |

## File Structure

```
mcp-a2a/
├── deck/                              ← 6 incremental decK state files
│   ├── 01-mcp-passthrough.yaml        ← MCP Passthrough Listener (native MCP proxy)
│   ├── 02-passthrough-auth.yaml       ← + Key-Auth + Rate-Limiting
│   ├── 03-conversion-listener.yaml    ← REST → MCP conversion (httpbin tools)
│   ├── 04-aggregation.yaml            ← Multi-team tool aggregation
│   ├── 05-mcp-oauth2.yaml             ← OAuth2 / PKCE with Keycloak
│   └── 06-a2a-routing.yaml            ← A2A agent routing + per-agent auth
├── mcp-server/                        ← MCP Travel Backend (flights, hotels, weather)
├── keycloak/
│   └── realm-workshop.json            ← Pre-configured Keycloak realm
├── docker-compose.yml                 ← MCP Backend + Keycloak
├── README.md                          ← This file (index)
└── README-DECK.md                     ← decK walkthrough (hands-on lab)
```

## Architecture

```
┌──────────────────────────────────┐
│  Konnect SaaS (Control Plane)   │
│  us.api.konghq.com              │
│  decK syncs config here         │
└──────────────┬───────────────────┘
               │ config sync
┌──────────────▼───────────────────┐
│  Kong Gateway DP (Docker)        │
│  Proxy: localhost:8000           │
└──────────────┬───────────────────┘
               │
    ┌──────────┼──────────┐
    ▼                     ▼
┌────────┐          ┌────────┐
│MCP     │          │Key-    │
│Backend │          │cloak   │
│:3001   │          │:8080   │
└────────┘          └────────┘
```

## MCP Modes

```
Is your upstream already an MCP server?
  ├── YES → passthrough-listener (Kong just proxies MCP traffic)
  └── NO (REST API)
        ├── Single backend? → conversion-listener (Kong converts MCP → REST)
        └── Multiple backends? → conversion-only (per team) + listener (aggregate)
```

| Mode | Client → Kong | Kong → Upstream | Use Case |
|------|--------------|-----------------|----------|
| `passthrough-listener` | MCP JSON-RPC | MCP JSON-RPC (unchanged) | MCP-native backend |
| `conversion-listener` | MCP JSON-RPC | REST HTTP calls | Existing REST APIs |
| `conversion-only` | — (no listener) | — (registers tools) | Per-team tool definitions |
| `listener` | MCP JSON-RPC | Aggregates tagged conversion-only tools | Unified multi-team endpoint |

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Kong Gateway 3.14+ / Konnect | Gateway runtime + Control Plane | [cloud.konghq.com](https://cloud.konghq.com) |
| Docker Desktop | Run MCP backend, Keycloak | [docker.com](https://www.docker.com/get-started) |
| decK CLI | Declarative Kong config | `brew install kong/deck/deck` |
| curl + jq | API testing | Pre-installed on macOS |

## Environment Variables

```bash
export KONNECT_TOKEN="<your-konnect-pat>"
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=http://localhost:8000
```

Verify:

```bash
deck gateway ping --konnect-token "$KONNECT_TOKEN" --konnect-control-plane-name "$CP_NAME"
```

## Quick Start

```bash
cd mcp-a2a
docker compose up -d --build
deck gateway sync deck/01-mcp-passthrough.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

## All Routes (after all steps)

| Route | Mode / Plugin | Auth | Purpose |
|-------|--------------|------|---------|
| `POST /mcp/tools` | passthrough-listener | key-auth + rate-limit | Native MCP clients |
| `POST /mcp/convert` | conversion-listener | — | REST APIs exposed as MCP |
| `POST /mcp/aggregate` | listener | — | Multi-team tool aggregation |
| `POST /mcp-oauth/tools` | passthrough-listener + ai-mcp-oauth2 | OAuth2 PKCE | VS Code, Claude, Insomnia |
| `GET /.well-known/agent.json` | — | — | A2A Agent Card |
| `POST /a2a/flights` | — | key-auth, 30/min | Flights sub-agent |
| `POST /a2a/hotels` | — | key-auth, 30/min | Hotels sub-agent |
| `POST /a2a/weather` | — | 60/min | Weather sub-agent |

## Teardown

```bash
deck gateway reset --force \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
docker compose down -v
```
