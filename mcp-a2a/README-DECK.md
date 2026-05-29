# Agentic AI Bootcamp — decK CLI Walkthrough

> 6-step hands-on lab using declarative `deck gateway` commands.
> Each step syncs a self-contained YAML file that **replaces** the
> previous gateway state. Steps are independent — test each step
> before moving to the next.

## Prerequisites

```bash
export KONNECT_TOKEN="<your-konnect-pat>"
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=http://localhost:8000
```

### Docker Services

```bash
cd mcp-a2a
docker compose up -d --build
```

This starts:
- **MCP Backend** (`localhost:3001`) — travel tools: flights, hotels, weather
- **Keycloak** (`localhost:8080`) — OIDC provider for Step 5

### Connect Kong DP to the backend network

Kong DP runs on Docker's default `bridge` network. The MCP backend and Keycloak run on `mcp-a2a_kong-net`. Connect Kong so it can resolve container hostnames:

```bash
# Find your Kong DP container name
docker ps --format '{{.Names}}\t{{.Image}}' | grep kong-gateway
# e.g. kong-dp

# Connect it to the mcp-a2a network
docker network connect mcp-a2a_kong-net <kong-dp-container-name>
```

**Fix Kong DNS** — If you get `name resolution failed` errors:

```bash
docker exec <kong-dp-container-name> sh -c \
  'echo "dns_resolver = 127.0.0.11" >> /etc/kong/kong.conf && kong reload'
```

### Verify

```bash
curl -s http://localhost:3001/health | jq '.'                        # MCP Backend
curl -s http://localhost:8080/realms/workshop | jq '.realm'          # Keycloak
deck gateway ping --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"                            # decK → Konnect
```

### Reset Gateway

Clear any existing configuration so you start from a clean slate:

```bash
deck gateway reset --force \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

---

## Step 1 — MCP Passthrough Listener

Client sends native MCP JSON-RPC → Kong forwards it unchanged → MCP backend processes it.

### 1.1 Sync

```bash
deck gateway sync deck/01-mcp-passthrough.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

### 1.2 Test — List tools

```bash
curl -s -X POST $PROXY_URL/mcp/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | jq '[.result.tools[].name]'
```

**Expected:** `["search_flights","book_flight","get_weather","search_hotels","book_hotel"]`

### 1.3 Test — Call a tool

```bash
curl -s -X POST $PROXY_URL/mcp/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0","id":2,
    "method":"tools/call",
    "params":{"name":"search_flights","arguments":{"origin":"SFO","destination":"LHR"}}
  }' | jq '.result.content[0].text | fromjson | .[0]'
```

**Expected:** Flight object with `airline`, `price`, `departure` fields.

---

## Step 2 — Key-Auth + Rate-Limiting

Protect the passthrough route with API key authentication and a 30 req/min rate limit.

### 2.1 Sync

```bash
deck gateway sync deck/02-passthrough-auth.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

### 2.2 Test — No key → 401

```bash
curl -si -X POST $PROXY_URL/mcp/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -1
```

**Expected:** `HTTP/1.1 401 Unauthorized`

### 2.3 Test — With key → 200 + rate-limit headers

```bash
curl -si -X POST $PROXY_URL/mcp/tools \
  -H "X-API-Key: mcp-key-001" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | grep -iE "^HTTP|x-ratelimit"
```

**Expected:**
```
HTTP/1.1 200 OK
X-RateLimit-Limit-Minute: 30
X-RateLimit-Remaining-Minute: 29
```

---

## Step 3 — Conversion Listener (REST → MCP)

Expose a plain REST API (httpbin) as MCP tools. Kong converts MCP JSON-RPC tool calls into standard HTTP requests — no changes to the backend required.

> **Note:** This step uses httpbin instead of the travel backend to demonstrate
> that conversion mode works with *any* existing REST API, not just MCP-aware services.

### 3.1 Sync

```bash
deck gateway sync deck/03-conversion-listener.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

> **Note:** This file includes `httpbin-service` + `httpbin-route` as prerequisites. If these already exist in your CP from another lab, decK merges them.

### 3.2 Test — Initialize session

Conversion mode uses MCP Streamable HTTP (SSE). Initialize a session first:

```bash
SESSION_ID=$(curl -si -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  2>&1 | grep -i "mcp-session-id" | awk '{print $2}' | tr -d '\r')
echo "Session: $SESSION_ID"
```

### 3.3 Test — List converted tools

```bash
curl -s -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | grep "^data:" | sed 's/^data: //' | jq '[.result.tools[].name]'
```

**Expected:** `["check_status","echo_anything","get_headers","get_ip","get_user_agent"]`

### 3.4 Test — Call get_ip (Kong converts to GET /httpbin/ip)

```bash
curl -s -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_ip","arguments":{}}}' \
  | grep "^data:" | sed 's/^data: //' | jq '.result.content[0].text'
```

**Expected:** JSON string containing `"origin": "<your-ip>"`

### 3.5 Test — Call echo_anything (Kong converts to POST /httpbin/anything)

```bash
curl -s -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"echo_anything","arguments":{"body":{"message":"Hello from MCP!"}}}}' \
  | grep "^data:" | sed 's/^data: //' | jq '.result.content[0].text | fromjson | .json'
```

**Expected:** `{"message": "Hello from MCP!"}`

---

## Step 4 — Multi-Team Aggregation

Three teams each own different tools. One aggregate endpoint merges them all. `conversion-only` plugins register tools (tagged `mcp-agg`), and a `listener` plugin discovers them.

> **Why httpbin?** Steps 3-4 demonstrate how Kong converts *any* REST API into MCP tools.
> The travel backend from steps 1-2 already speaks MCP natively — here we show Kong
> making a plain REST API (httpbin) available to MCP clients without any code changes.

```
              /mcp/aggregate (listener, discovers tag: mcp-agg)
              ├── /mcp/team-alpha   (conversion-only: get_ip, get_headers)
              ├── /mcp/team-beta    (conversion-only: get_user_agent, echo_anything)
              └── /mcp/team-gamma   (conversion-only: check_status)
```

### 4.1 Sync

```bash
deck gateway sync deck/04-aggregation.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

### 4.2 Test — Initialize + list all tools

```bash
# Initialize
INIT_RAW=$(curl -si -X POST $PROXY_URL/mcp/aggregate \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' 2>&1)

AGG_SESSION=$(echo "$INIT_RAW" | grep -i "mcp-session-id" | tr -d '\r' | awk '{print $2}')
echo "Session: $AGG_SESSION"

# List all tools from all 3 teams
curl -s -X POST $PROXY_URL/mcp/aggregate \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${AGG_SESSION}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | grep "^data:" | sed 's/^data: //' | jq '[.result.tools[].name]'
```

**Expected:** `["check_status","echo_anything","get_headers","get_ip","get_user_agent"]` — all 5 tools from 3 teams.

### 4.3 Test — Call tools from different teams

```bash
# get_ip (from team-alpha)
curl -s -X POST $PROXY_URL/mcp/aggregate \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${AGG_SESSION}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_ip","arguments":{}}}' \
  | grep "^data:" | sed 's/^data: //' | jq '.result.content[0].text'

# echo_anything (from team-beta)
curl -s -X POST $PROXY_URL/mcp/aggregate \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${AGG_SESSION}" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo_anything","arguments":{}}}' \
  | grep "^data:" | sed 's/^data: //' | jq '.result.content[0].text | fromjson | .method'
```

**Expected:** IP address string, then `"GET"`.

---

## Step 5 — MCP + OAuth2 / PKCE

API keys work for demos. Production MCP clients (VS Code Copilot, Claude Desktop, Insomnia) need OAuth2. The `ai-mcp-oauth2` plugin validates tokens against Keycloak.

> **Rule:** `ai-mcp-oauth2` MUST pair with `passthrough-listener` — never with `conversion-listener`.

```
Client ──► GET /authorize + PKCE ──► Keycloak
       ◄── auth code ──────────────
       ──► Exchange code + verifier ──► Keycloak
       ◄── Access token (JWT) ────────
       ──► POST /mcp-oauth/tools + Bearer token ──► Kong ──► MCP Backend
```

### 5.1 Sync

```bash
deck gateway sync deck/05-mcp-oauth2.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

### 5.2 Test — No token → 401

```bash
curl -si -X POST $PROXY_URL/mcp-oauth/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -1
```

**Expected:** `HTTP/1.1 401 Unauthorized`

### 5.3 Test — Get token from Keycloak + call

```bash
TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/workshop/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=mcp-oauth-client" \
  -d "client_secret=mcp-oauth-secret" \
  | jq -r '.access_token')
echo "Token (first 40 chars): ${TOKEN:0:40}..."

curl -s -X POST $PROXY_URL/mcp-oauth/tools \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | jq '[.result.tools[].name]'
```

**Expected:** `["search_flights","book_flight","get_weather","search_hotels","book_hotel"]`

### 5.4 Connect VS Code Copilot

The `.vscode/mcp.json` supports OAuth2:

```json
{
  "servers": {
    "kong-travel-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp-oauth/tools",
      "headers": { "Content-Type": "application/json" },
      "auth": {
        "type": "oauth2",
        "authorizationUrl": "http://localhost:8080/realms/workshop/protocol/openid-connect/auth",
        "tokenUrl": "http://localhost:8080/realms/workshop/protocol/openid-connect/token",
        "clientId": "mcp-oauth-client",
        "scopes": ["openid", "profile", "mcp-tools"],
        "pkce": true
      }
    }
  }
}
```

`Ctrl+Shift+P` → **GitHub Copilot: Open MCP Tools** → `kong-travel-mcp` → first call triggers browser login.

### 5.5 Connect Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kong-travel": {
      "type": "http",
      "url": "http://localhost:8000/mcp-oauth/tools",
      "oauth": {
        "clientId": "mcp-oauth-client",
        "authorizationUrl": "http://localhost:8080/realms/workshop/protocol/openid-connect/auth",
        "tokenUrl": "http://localhost:8080/realms/workshop/protocol/openid-connect/token",
        "scopes": ["openid", "mcp-tools"],
        "pkce": true
      }
    }
  }
}
```

---

## Step 6 — A2A Agent Routing

Kong routes agent-to-agent traffic. Each sub-agent gets its own route, auth, and rate limit. No special A2A plugin — standard Kong plugins handle everything.

```
Orchestrator Agent
     │
     ├── GET  /.well-known/agent.json   → Agent Card (public, no auth)
     ├── POST /a2a/flights              → key-auth, 30 req/min
     ├── POST /a2a/hotels               → key-auth, 30 req/min
     └── POST /a2a/weather              → no auth,  60 req/min
```

### 6.1 Sync

```bash
deck gateway sync deck/06-a2a-routing.yaml \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
```

### 6.2 Test — Agent Card discovery

```bash
curl -s $PROXY_URL/.well-known/agent.json | jq '{name: .name, skills: [.skills[].id]}'
```

**Expected:** `{"name": "TravelOrchestratorAgent", "skills": ["flight-search","hotel-booking","weather-check"]}`

### 6.3 Test — No key → 401

```bash
curl -si -X POST $PROXY_URL/a2a/flights \
  -H "Content-Type: application/json" \
  -d '{"id":"t1","message":{"role":"user","parts":[{"type":"text","text":"SFO to LHR"}]}}' \
  | head -1
```

**Expected:** `HTTP/1.1 401 Unauthorized`

### 6.4 Test — With key → 200

```bash
curl -s -X POST $PROXY_URL/a2a/flights \
  -H "X-Agent-Key: orchestrator-key-xyz" \
  -H "Content-Type: application/json" \
  -d '{"id":"t1","message":{"role":"user","parts":[{"type":"text","text":"SFO to LHR June 15"}]}}' \
  | jq '.result.parts[0].text | fromjson | .[0]'
```

**Expected:** Flight object with `airline`, `price`, `departure`.

### 6.5 Test — Weather (no auth, different rate limit)

```bash
curl -si -X POST $PROXY_URL/a2a/weather \
  -H "Content-Type: application/json" \
  -d '{"id":"t3","message":{"role":"user","parts":[{"type":"text","text":"Weather at LHR"}]}}' \
  | grep -iE "^HTTP|x-ratelimit-limit"
```

**Expected:**
```
HTTP/1.1 200 OK
X-RateLimit-Limit-Minute: 60
```

### 6.6 Test — Full A2A delegation

```bash
# Flights
curl -s -X POST $PROXY_URL/a2a/flights \
  -H "X-Agent-Key: orchestrator-key-xyz" \
  -H "Content-Type: application/json" \
  -d '{"id":"task-001","message":{"role":"user","parts":[{"type":"text","text":"Round-trip SFO to LHR June 15-22"}]}}' \
  | jq '.result.parts[0].text | fromjson | .[0]'

# Hotels (use airport code LHR — backend matches on 3-letter codes)
curl -s -X POST $PROXY_URL/a2a/hotels \
  -H "X-Agent-Key: orchestrator-key-xyz" \
  -H "Content-Type: application/json" \
  -d '{"id":"task-002","message":{"role":"user","parts":[{"type":"text","text":"Hotels near LHR June 15-22"}]}}' \
  | jq '.result.parts[0].text | fromjson | .[0]'

# Weather (no key)
curl -s -X POST $PROXY_URL/a2a/weather \
  -H "Content-Type: application/json" \
  -d '{"id":"task-003","message":{"role":"user","parts":[{"type":"text","text":"Weather at LHR June 15"}]}}' \
  | jq '.result.parts[0].text | fromjson'
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `name resolution failed` for mcp-backend | `docker network connect mcp-a2a_kong-net <kong-dp>` and fix DNS resolver |
| `already exists in network` | Safe to ignore — Kong is already connected |
| Step 3/4 tool calls return 404 | Tool `path` must match an existing Kong route (e.g. `/httpbin/ip` → httpbin-route) |
| OAuth2 returns 401 with valid token | Check `jwks_endpoint` uses Docker hostname (`keycloak:8080`), not `localhost` |
| A2A hotels returns empty results | Use 3-letter airport codes (LHR, CDG) — backend matches on `location === code` |

## Cleanup

```bash
deck gateway reset --force \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$CP_NAME"
docker compose down -v
```
