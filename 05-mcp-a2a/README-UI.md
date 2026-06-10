# Agentic AI Bootcamp - Konnect UI Walkthrough (Serverless)

> 6-step hands-on lab using the Konnect web console. Each step adds one
> self-contained slice of MCP / A2A configuration. Steps are independent —
> test each one before moving on.

> **What you bring forward from the previous modules:** Kong's job in MCP
> and A2A is the *same* job it had in api-gateway - route, authenticate,
> rate-limit, observe. There is no "agent gateway"; there are standard
> gateway plugins (`key-auth`, `rate-limiting`) paired with two MCP-aware
> plugins (`ai-mcp-proxy`, `ai-mcp-oauth2`). If you understood Step 05 of
> api-gateway, you already understand Step 2 here. Read the **Concepts**
> section below for the four new ideas (MCP, listener modes, PKCE, A2A)
> before touching any plugin.

---

## Concepts - Read This First

This bootcamp introduces four ideas that aren't covered in the earlier
api-gateway / apiops / ai-gateway modules. Skim these definitions before
clicking into the Konnect console.

### MCP (Model Context Protocol)

MCP is the open protocol AI assistants (Claude Desktop, GitHub Copilot,
Cursor) use to discover and call **tools** - small, well-described functions
the LLM can invoke. Instead of every assistant inventing its own plugin
format, MCP standardises:

- A wire format (JSON-RPC 2.0 over HTTP or stdio).
- A handshake (`initialize`) that returns the server's capabilities.
- A tool catalog (`tools/list`) and a way to invoke one (`tools/call`).
- Optional `resources/*` and `prompts/*` methods for non-tool capabilities.

A request to an MCP server looks like a plain HTTP POST whose body is a
JSON-RPC envelope:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

The server replies with `{"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}`.

### Kong's four MCP listener modes

Kong's `ai-mcp-proxy` plugin can stand in front of MCP traffic in four
shapes. Pick one per route:

| Mode | Client sends | Kong forwards as | Use when |
|---|---|---|---|
| `passthrough-listener` | MCP JSON-RPC | MCP JSON-RPC (unchanged) | Upstream is already an MCP server. |
| `conversion-listener` | MCP JSON-RPC | REST HTTP | You have a REST API and want it usable from MCP clients. |
| `conversion-only` | - (no listener) | - (just declares tools) | Per-team REST APIs that will be aggregated elsewhere. |
| `listener` (aggregate) | MCP JSON-RPC | Multiple upstreams via tagged `conversion-only` plugins | Multi-team catalog: one MCP endpoint, many backends. |

Steps 1–4 walk through each in turn. Steps 5–6 layer auth on top.

### PKCE (Proof Key for Code Exchange)

OAuth2's "authorization code" flow normally pairs a code with a client
**secret** during token exchange. That's fine for a backend, fatal for a
desktop app: the binary ships to laptops, anyone can extract the secret.

PKCE replaces the static secret with a one-time, per-request proof:

1. The client generates a random `code_verifier` (43–128 chars).
2. Hashes it (`code_challenge = SHA256(code_verifier)`).
3. Sends the **challenge** with the authorization request.
4. Gets back an auth `code` and exchanges it together with the **verifier**.

The IdP recomputes the hash and only issues a token if the values match.
The verifier never travels with the code, so intercepting either alone is
useless. Step 5's "Flow B" runs this by hand with `openssl` so you can see
each piece.

### A2A (Agent-to-Agent)

A2A is the emerging convention for **agents calling other agents**. An
orchestrator agent doesn't pick one model and shell out - it routes work to
specialised sub-agents (a flights agent, a hotels agent, a weather agent)
and merges their answers. The wire format mirrors MCP enough that JSON-RPC
clients can talk to it, with one addition: an **Agent Card** served from
`/.well-known/agent.json` that advertises which skills the agent owns and
how to reach them.

Kong's role in A2A is exactly its role in any API: route, authenticate,
rate-limit, observe. No special A2A plugin - Step 6 wires up sub-agents
using the standard `key-auth` and `rate-limiting` plugins you've already
seen in api-gateway.

### How the auth story progresses

The six steps escalate auth deliberately:

| Step | Auth on the route | Why |
|---|---|---|
| 1 | None | First, prove the protocol works. |
| 2 | `key-auth` + `rate-limiting` | Server-to-server callers; same model as api-gateway Step 05. |
| 3 | None | Focus on REST→MCP conversion, not auth. |
| 4 | None | Focus on multi-team aggregation, not auth. |
| 5 | `ai-mcp-oauth2` (JWT bearer) | Real MCP clients (VS Code, Claude Desktop) - `client_credentials` for backends, PKCE for desktops. |
| 6 | Per-sub-agent (key-auth on some, open on others) | Trust isolation between sibling agents. |

Each step's "Why this auth?" callout assumes you've read the table above.

---

## Prerequisites

1. **Konnect account** at [cloud.konghq.com](https://cloud.konghq.com)
2. **Control Plane** `<your-control-plane>` with a Konnect Serverless Data Plane
3. **Proxy URL** - your Konnect serverless proxy URL

```bash
export PROXY_URL="<your-serverless-proxy-url>"   # e.g. https://abc123.kong-proxy.com
```

### Auth0 Tenant (Step 5 only)

Step 5 (OAuth2/PKCE) requires an Auth0 tenant. Set up the following:

1. **Machine-to-Machine Application** (for `client_credentials` flow)
   - Note the **Client ID** and **Client Secret**
2. **Single Page Application** with PKCE enabled (for `authorization_code` flow)
   - Set **Allowed Callback URLs** to: `$PROXY_URL/mcp-oauth/callback`
   - Note the **Client ID**
3. **API** (audience) for token validation
4. **Test users** (optional, for PKCE flow):
   - `agent-user@bootcamp.dev` / `Agent123!`

```bash
export AUTH0_DOMAIN="<your-tenant>.us.auth0.com"
```

### Docker Services + ngrok

The MCP backend runs locally in Docker. The Konnect Serverless DP cannot
reach Docker services directly, so you need **ngrok** to create public
tunnels.

```bash
cd 05-mcp-a2a
docker compose up -d --build          # MCP backend (travel tools)
```

Expose the MCP backend via ngrok:

```bash
ngrok http 3001
# → Forwarding  https://abc123.ngrok-free.app -> http://localhost:3001
```

Copy the ngrok HTTPS URL and note the hostname (e.g. `abc123.ngrok-free.app`).

> **Steps 3-4** use httpbun.com (external) -- no ngrok needed.

### Verify

```bash
curl -s http://localhost:3001/health | jq '.'                        # MCP Backend (local)
curl -s https://<ngrok-hostname>/health | jq '.'                     # MCP Backend (via ngrok)
```

### Reset Gateway

Before starting, delete any pre-existing services in
**Gateway Manager → `<your-control-plane>` → Services** so you start clean.

---

## Step 1 - MCP Passthrough Listener

Client sends native MCP JSON-RPC → Kong forwards it unchanged → MCP backend
processes it. The upstream already speaks MCP, so the `ai-mcp-proxy` plugin
only has to enforce the protocol shape - no translation.

### 1.1 Create the Service

1. Go to **Gateway Manager → `<your-control-plane>` → Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `mcp-backend`
   - **Protocol**: `https`
   - **Host**: `<ngrok-hostname>` *(e.g. `abc123.ngrok-free.app`)*
   - **Port**: `443`
   - **Tags**: `mcp`
4. Click **Save**

### 1.2 Create the Route

1. On the service detail page, go to the **Routes** tab
2. Click **New Route**
3. Configure:
   - **Name**: `mcp-passthrough`
   - **Path(s)**: `/mcp/tools`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `off`
   - **Tags**: `passthrough`
4. Click **Save**

### 1.3 Add the AI MCP Proxy Plugin

1. On the route detail page, go to the **Plugins** tab
2. Click **New Plugin → AI → AI MCP Proxy**
3. Configure:
   - **Mode**: `passthrough-listener`
4. Click **Save**

### 1.4 Test - List tools

```bash
curl -s -X POST $PROXY_URL/mcp/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | jq '[.result.tools[].name]'
```

**Expected:** `["search_flights","book_flight","get_weather","search_hotels","book_hotel"]`

### 1.5 Test - Call a tool

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

## Step 2 - Key-Auth + Rate-Limiting

Protect the passthrough route with API key authentication and a 30 req/min
rate limit. This is the same pattern you used in api-gateway Step 05 - MCP
adds nothing new to auth here.

### 2.1 Create the Consumer

1. Go to **Gateway Manager → `<your-control-plane>` → Consumers**
2. Click **New Consumer**
3. Configure:
   - **Username**: `mcp-user`
   - **Tags**: `mcp`
4. Click **Save**
5. On the consumer detail page, go to the **Credentials** tab
6. Click **New Key Authentication Credential**
7. Configure:
   - **Key**: `mcp-key-001`
8. Click **Save**

### 2.2 Add Key-Auth to the Route

1. Navigate to the **mcp-passthrough** route → **Plugins** tab
2. Click **New Plugin → Authentication → Key Authentication**
3. Configure:
   - **Key Names**: `X-API-Key`
   - **Hide Credentials**: `on`
4. Click **Save**

### 2.3 Add Rate-Limiting to the Route

1. Still on the **mcp-passthrough** route → **Plugins** tab
2. Click **New Plugin → Traffic Control → Rate Limiting**
3. Configure:
   - **Minute**: `30`
   - **Policy**: `local`
4. Click **Save**

### 2.4 Test - No key → 401

```bash
curl -si -X POST $PROXY_URL/mcp/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -1
```

**Expected:** `HTTP/1.1 401 Unauthorized`

### 2.5 Test - With key → 200 + rate-limit headers

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

## Step 3 - Conversion Listener (REST → MCP)

Expose a plain REST API (httpbun) as MCP tools. Kong converts MCP JSON-RPC
tool calls into standard HTTP requests - no changes to the backend required.

> **Note:** This step uses httpbun instead of the travel backend to
> demonstrate that conversion mode works with *any* existing REST API, not
> just MCP-aware services.

### 3.1 Create the httpbun Service

1. Go to **Gateway Manager → `<your-control-plane>` → Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `httpbun-service`
   - **Protocol**: `https`
   - **Host**: `httpbun.com`
   - **Port**: `443`
4. Click **Save**

### 3.2 Create the Plain REST Route

1. On `httpbun-service` → **Routes** tab → **New Route**
2. Configure:
   - **Name**: `httpbun-route`
   - **Path(s)**: `/httpbun`
   - **Strip Path**: `on`
3. Click **Save**

> Why this route matters: the conversion-listener plugin's tool paths
> (`/httpbun/ip`, `/httpbun/headers`, …) must resolve to an existing Kong
> route. This `httpbun-route` is what those internal calls hit.

### 3.3 Create the Conversion Route

1. Still on `httpbun-service` → **Routes** tab → **New Route**
2. Configure:
   - **Name**: `mcp-conversion`
   - **Path(s)**: `/mcp/convert`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `on`
   - **Tags**: `conversion`
3. Click **Save**

### 3.4 Add the AI MCP Proxy Plugin (conversion-listener)

1. Navigate to the **mcp-conversion** route → **Plugins** tab
2. Click **New Plugin → AI → AI MCP Proxy**
3. Configure:
   - **Mode**: `conversion-listener`
   - **Server → Timeout**: `60000`
4. Add **Tools** (click **+ Add Tool** for each):

   **Tool 1 - get_ip**
   - **Name**: `get_ip`
   - **Description**: `Get the origin IP address of the caller`
   - **Method**: `GET`
   - **Path**: `/httpbun/ip`
   - **Annotations → Title**: `Get IP`

   **Tool 2 - get_headers**
   - **Name**: `get_headers`
   - **Description**: `Get the request headers as seen by the server`
   - **Method**: `GET`
   - **Path**: `/httpbun/headers`
   - **Annotations → Title**: `Get Headers`

   **Tool 3 - get_user_agent**
   - **Name**: `get_user_agent`
   - **Description**: `Get the User-Agent string of the caller`
   - **Method**: `GET`
   - **Path**: `/httpbun/user-agent`
   - **Annotations → Title**: `Get User Agent`

   **Tool 4 - echo_anything**
   - **Name**: `echo_anything`
   - **Description**: `Echo back any data sent to the server`
   - **Method**: `POST`
   - **Path**: `/httpbun/anything`
   - **Annotations → Title**: `Echo Anything`
   - **Request Body → Content → application/json → Schema**:
     ```json
     {
       "type": "object",
       "properties": {
         "message": { "type": "string", "description": "Message to echo" }
       }
     }
     ```

   **Tool 5 - check_status**
   - **Name**: `check_status`
   - **Description**: `Get an HTTP response with the specified status code`
   - **Method**: `GET`
   - **Path**: `/httpbun/status/{code}`
   - **Annotations → Title**: `Check Status`
   - **Parameters → + Add Parameter**:
     - **Name**: `code`
     - **In**: `path`
     - **Required**: `on`
     - **Schema → Type**: `integer`
     - **Description**: `HTTP status code to return (e.g. 200, 404, 500)`

5. Click **Save**

### 3.5 Test - Initialize session

Conversion mode uses MCP Streamable HTTP (SSE). Initialize a session first:

```bash
SESSION_ID=$(curl -si -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  2>&1 | grep -i "mcp-session-id" | awk '{print $2}' | tr -d '\r')
echo "Session: $SESSION_ID"
```

### 3.6 Test - List converted tools

```bash
curl -s -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | grep "^data:" | sed 's/^data: //' | jq '[.result.tools[].name]'
```

**Expected:** `["check_status","echo_anything","get_headers","get_ip","get_user_agent"]`

### 3.7 Test - Call get_ip (Kong converts to GET /httpbun/ip)

```bash
curl -s -X POST $PROXY_URL/mcp/convert \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_ip","arguments":{}}}' \
  | grep "^data:" | sed 's/^data: //' | jq '.result.content[0].text'
```

**Expected:** JSON string containing `"origin": "<your-ip>"`

### 3.8 Test - Call echo_anything (Kong converts to POST /httpbun/anything)

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

## Step 4 - Multi-Team Aggregation

Three teams each own different tools. One aggregate endpoint merges them
all. `conversion-only` plugins register tools (tagged `mcp-agg`), and a
`listener` plugin discovers them.

> **Why httpbun?** Steps 3-4 demonstrate how Kong converts *any* REST API
> into MCP tools. The travel backend from steps 1-2 already speaks MCP
> natively - here we show Kong making a plain REST API (httpbun) available
> to MCP clients without any code changes.

```
              /mcp/aggregate (listener, discovers tag: mcp-agg)
              ├── /mcp/team-alpha   (conversion-only: get_ip, get_headers)
              ├── /mcp/team-beta    (conversion-only: get_user_agent, echo_anything)
              └── /mcp/team-gamma   (conversion-only: check_status)
```

> **Prerequisite:** `httpbun-service` and `httpbun-route` must already
> exist from Step 3. If you reset between steps, recreate them per 3.1–3.2.

### 4.1 Create the team-alpha Route

1. On `httpbun-service` → **Routes** tab → **New Route**
2. Configure:
   - **Name**: `mcp-team-alpha`
   - **Path(s)**: `/mcp/team-alpha`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `on`
   - **Tags**: `mcp-agg`
3. Click **Save**

### 4.2 Add Conversion-Only Plugin to team-alpha

1. On the `mcp-team-alpha` route → **Plugins** tab
2. Click **New Plugin → AI → AI MCP Proxy**
3. Configure:
   - **Mode**: `conversion-only`
   - **Tags**: `mcp-agg` *(critical - the listener discovers tools by this tag)*
4. Add **Tools**:
   - **get_ip** - `GET /httpbun/ip` - *Get origin IP address*
   - **get_headers** - `GET /httpbun/headers` - *Get all HTTP request headers*
5. Click **Save**

### 4.3 Create the team-beta Route + Plugin

1. New Route on `httpbun-service`:
   - **Name**: `mcp-team-beta`
   - **Path(s)**: `/mcp/team-beta`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `on`
   - **Tags**: `mcp-agg`
2. Click **Save**, then add **New Plugin → AI → AI MCP Proxy**:
   - **Mode**: `conversion-only`
   - **Tags**: `mcp-agg`
   - **Tools**:
     - **get_user_agent** - `GET /httpbun/user-agent` - *Get User-Agent string*
     - **echo_anything** - `POST /httpbun/anything` - *Echo back anything sent*
3. Click **Save**

### 4.4 Create the team-gamma Route + Plugin

1. New Route on `httpbun-service`:
   - **Name**: `mcp-team-gamma`
   - **Path(s)**: `/mcp/team-gamma`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `on`
   - **Tags**: `mcp-agg`
2. Click **Save**, then add **New Plugin → AI → AI MCP Proxy**:
   - **Mode**: `conversion-only`
   - **Tags**: `mcp-agg`
   - **Tools**:
     - **check_status** - `GET /httpbun/status/{code}` - *Get HTTP response with given status code*
       - **Parameters → code**: `in: path`, `required: on`, `schema.type: integer`
3. Click **Save**

### 4.5 Create the Aggregate Route + Listener Plugin

1. New Route on `httpbun-service`:
   - **Name**: `mcp-aggregate`
   - **Path(s)**: `/mcp/aggregate`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `on`
   - **Tags**: `aggregation`
2. Click **Save**, then add **New Plugin → AI → AI MCP Proxy**:
   - **Mode**: `listener`
   - **Server → Tag**: `mcp-agg` *(this is the magic - Kong discovers every `conversion-only` plugin tagged `mcp-agg`)*
3. Click **Save**

### 4.6 Test - Initialize + list all tools

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

**Expected:** `["check_status","echo_anything","get_headers","get_ip","get_user_agent"]` - all 5 tools from 3 teams.

### 4.7 Test - Call tools from different teams

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

## Step 5 - MCP + OAuth2 (two flows)

API keys work for demos. Real MCP clients need OAuth2 - and the *right*
OAuth2 flow depends on **who the client is**:

| Caller | Flow | Why |
|--------|------|-----|
| Server-to-server (CI, backend orchestrator) | `client_credentials` | No human in the loop; the caller can safely hold a client secret. |
| Desktop / CLI / IDE (VS Code, Claude Desktop) | `authorization_code` + **PKCE** | No safe way to ship a client secret in a binary that ships to every laptop. PKCE replaces the secret with a one-time, per-request proof. |

This step demonstrates **both**. The `ai-mcp-oauth2` plugin validates the
issued JWT either way - Kong doesn't care which OAuth2 flow produced the token.

> **Rule:** `ai-mcp-oauth2` MUST pair with `passthrough-listener` - never with `conversion-listener`.

```
                       ┌───────── Auth0 Tenant ──────────────────────┐
                       │  mcp-service-app  (M2M, client_credentials) │
                       │  mcp-pkce-app     (SPA, PKCE-only)          │
                       └─────────────────────────────────────────────┘
                                       ▲                ▲
                                       │ client_creds   │ auth_code + PKCE
                                       │                │
                              ┌────────┴───┐    ┌───────┴──────┐
                              │ curl / CI  │    │ VS Code etc. │
                              └────────┬───┘    └──────────────┘
                                       │  Bearer <JWT>
                                       ▼
                            POST /mcp-oauth/tools
                               (Kong validates JWT → ai-mcp-proxy)
```

### 5.1 Create the OAuth-Protected Service

1. Go to **Gateway Manager → `<your-control-plane>` → Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `mcp-backend-oauth`
   - **Protocol**: `https`
   - **Host**: `<ngrok-hostname>` *(e.g. `abc123.ngrok-free.app`)*
   - **Port**: `443`
   - **Path**: `/mcp` *(the backend's MCP endpoint lives under `/mcp`)*
   - **Tags**: `mcp`, `oauth`
4. Click **Save**

### 5.2 Create the OAuth Route

1. On `mcp-backend-oauth` → **Routes** tab → **New Route**
2. Configure:
   - **Name**: `mcp-oauth`
   - **Path(s)**: `/mcp-oauth`
   - **Method(s)**: `POST`, `GET`
   - **Strip Path**: `on`
   - **Tags**: `oauth2`
3. Click **Save**

### 5.3 Add the AI MCP OAuth2 Plugin

1. On the `mcp-oauth` route → **Plugins** tab
2. Click **New Plugin → AI → AI MCP OAuth2**
3. Configure:
   - **Resource**: `$PROXY_URL/mcp-oauth/tools`
   - **Authorization Servers** (add one entry): `https://<AUTH0_DOMAIN>/`
   - **JWKS Endpoint**: `https://<AUTH0_DOMAIN>/.well-known/jwks.json`
   - **Insecure Relaxed Audience Validation**: `on`
     *(DEMO ONLY - relaxes RFC 8707 audience binding so a token issued without an explicit `audience` claim still validates. Do NOT ship this to production.)*
   - **Claim to Header** (add two entries):
     - **Claim**: `sub` → **Header**: `X-User-Id`
     - **Claim**: `preferred_username` → **Header**: `X-User-Name`
4. Click **Save**

### 5.4 Add the AI MCP Proxy Plugin (passthrough-listener)

1. Still on the `mcp-oauth` route → **Plugins** tab
2. Click **New Plugin → AI → AI MCP Proxy**
3. Configure:
   - **Mode**: `passthrough-listener`
4. Click **Save**

### 5.5 Test - No token → 401

```bash
curl -si -X POST $PROXY_URL/mcp-oauth/tools \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -1
```

**Expected:** `HTTP/1.1 401 Unauthorized`

### 5.6 Flow A - `client_credentials` (server-to-server)

Uses the **Machine-to-Machine** Auth0 application `mcp-service-app`. The
client holds a secret; Auth0 returns an access token directly. No browser,
no user.

```bash
TOKEN=$(curl -s -X POST \
  https://$AUTH0_DOMAIN/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<AUTH0_M2M_CLIENT_ID>" \
  -d "client_secret=<AUTH0_M2M_CLIENT_SECRET>" \
  -d "audience=<AUTH0_API_AUDIENCE>" \
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

> **What you just proved:** A trusted backend can mint its own tokens
> against the IdP and call MCP tools without any user interaction. The
> secret never leaves your infrastructure.

### 5.7 Flow B - `authorization_code` + PKCE (by hand)

Uses the **SPA** Auth0 application `mcp-pkce-app` (no secret). The client
generates a random `code_verifier`, hashes it to a `code_challenge`, sends the
challenge with the auth request, and proves possession of the verifier when
exchanging the code for a token. This is what VS Code and Claude Desktop do
automatically - here we do it step by step so you can see it.

```bash
# 1. Generate a PKCE code_verifier (43-128 chars, URL-safe) and its S256 challenge
VERIFIER=$(openssl rand -base64 64 | tr -d '/+=\n' | cut -c1-64)
CHALLENGE=$(printf %s "$VERIFIER" | openssl dgst -sha256 -binary \
            | openssl base64 | tr -d '=\n' | tr '/+' '_-')
echo "verifier:  $VERIFIER"
echo "challenge: $CHALLENGE"

# 2. Open this URL in a browser, sign in with your Auth0 user,
#    and paste back the `code=...` value from the redirect URL.
echo "https://$AUTH0_DOMAIN/authorize?\
client_id=<AUTH0_SPA_CLIENT_ID>&\
response_type=code&\
scope=openid+profile&\
redirect_uri=$PROXY_URL/mcp-oauth/callback&\
code_challenge=$CHALLENGE&\
code_challenge_method=S256&\
audience=<AUTH0_API_AUDIENCE>"

read -p "Paste the code from the redirect URL: " CODE

# 3. Exchange the code + verifier for a token (no client_secret).
TOKEN=$(curl -s -X POST \
  https://$AUTH0_DOMAIN/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=<AUTH0_SPA_CLIENT_ID>" \
  -d "code=$CODE" \
  -d "redirect_uri=$PROXY_URL/mcp-oauth/callback" \
  -d "code_verifier=$VERIFIER" \
  | jq -r '.access_token')
echo "Token (first 40 chars): ${TOKEN:0:40}..."

# 4. Call Kong with the user-bound token.
curl -s -X POST $PROXY_URL/mcp-oauth/tools \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | jq '[.result.tools[].name]'
```

**Expected:** same five tool names as Flow A. The difference is *who the
token is bound to* - Flow A's `sub` is the service account; Flow B's `sub`
is the authenticated user. Inspect the token at [jwt.io](https://jwt.io) to compare.

> **What you just proved:** A desktop app with no secret can still get a
> user-scoped token. The `code_verifier` never touches the wire until the
> exchange, and the `code` alone is useless without it.

### 5.8 Connect VS Code Copilot

VS Code does PKCE for you. Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "kong-travel-mcp": {
      "type": "http",
      "url": "<PROXY_URL>/mcp-oauth/tools",
      "headers": { "Content-Type": "application/json" },
      "auth": {
        "type": "oauth2",
        "authorizationUrl": "https://<AUTH0_DOMAIN>/authorize",
        "tokenUrl": "https://<AUTH0_DOMAIN>/oauth/token",
        "clientId": "<AUTH0_SPA_CLIENT_ID>",
        "scopes": ["openid", "profile"],
        "pkce": true
      }
    }
  }
}
```

`Ctrl+Shift+P` → **GitHub Copilot: Open MCP Tools** → `kong-travel-mcp` →
first call triggers browser login.

### 5.9 Connect Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kong-travel": {
      "type": "http",
      "url": "<PROXY_URL>/mcp-oauth/tools",
      "oauth": {
        "clientId": "<AUTH0_SPA_CLIENT_ID>",
        "authorizationUrl": "https://<AUTH0_DOMAIN>/authorize",
        "tokenUrl": "https://<AUTH0_DOMAIN>/oauth/token",
        "scopes": ["openid", "profile"],
        "pkce": true
      }
    }
  }
}
```

### 5.10 (Exploration) Swap Auth0 for Kong Identity

Auth0 works well, but introduces a separate identity provider to manage.
**Kong Identity** is Konnect's built-in identity service - it lets you issue
OIDC tokens (including PKCE flows) without standing up a separate IdP. The
`ai-mcp-oauth2` plugin doesn't care who issued the JWT, so the swap is
mechanical - re-edit the plugin from 5.3 and change these fields:

| What changes | Auth0 | Kong Identity |
|---|---|---|
| **Authorization Servers** | `https://<AUTH0_DOMAIN>/` | `https://<your-org>.id.konghq.com` (issuer URL from the Kong Identity console) |
| **JWKS Endpoint** | `https://<AUTH0_DOMAIN>/.well-known/jwks.json` | `https://<your-org>.id.konghq.com/.well-known/jwks.json` |
| Where you create the clients | Auth0 Dashboard → Applications | **Konnect → Identity → Applications** |
| **Insecure Relaxed Audience Validation** | `on` (demo) | `off` - Kong Identity issues RFC-8707-compliant `aud` claims, so strict validation works out of the box |

When to actually use Kong Identity:
- Single pane of glass for *all* Konnect product auth (Dev Portal, Gateway, AI Gateway, MCP, Mesh).
- No second IdP to operate, patch, or back up.
- Identity scope tied to your Konnect org and RBAC - same teams, same audit trail.

When to stick with Auth0 (or your existing IdP):
- You already federate workforce identity through Auth0 / Okta / Azure AD / Ping and
  want one source of truth across products outside Konnect.
- You need protocols Kong Identity doesn't expose yet (e.g., raw SAML).

In a customer engagement, **the first question to ask is "do you have an
IdP already, and if not, do you want Konnect to be it?"** before designing
around either.

---

## Step 6 - A2A Agent Routing

Kong routes agent-to-agent traffic. Each sub-agent gets its own route,
auth, and rate limit. No special A2A plugin - standard Kong plugins handle
everything.

```
Orchestrator Agent
     │
     ├── GET  /.well-known/agent.json   → Agent Card (public, no auth)
     ├── POST /a2a/flights              → key-auth, 30 req/min
     ├── POST /a2a/hotels               → key-auth, 30 req/min
     └── POST /a2a/weather              → no auth,  60 req/min
```

### 6.1 Create the A2A Service

1. Go to **Gateway Manager → `<your-control-plane>` → Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `a2a-backend`
   - **Protocol**: `https`
   - **Host**: `<ngrok-hostname>` *(e.g. `abc123.ngrok-free.app`)*
   - **Port**: `443`
   - **Tags**: `a2a`
4. Click **Save**

### 6.2 Create the Orchestrator Consumer

1. Go to **Gateway Manager → `<your-control-plane>` → Consumers → New Consumer**
2. Configure:
   - **Username**: `orchestrator-agent`
   - **Tags**: `a2a`
3. Click **Save**
4. On the consumer detail page → **Credentials → New Key Authentication Credential**:
   - **Key**: `orchestrator-key-xyz`
5. Click **Save**

### 6.3 Create the Agent Card Route (public)

1. On `a2a-backend` → **Routes → New Route**
2. Configure:
   - **Name**: `a2a-discovery`
   - **Path(s)**: `/.well-known/agent.json`
   - **Method(s)**: `GET`
   - **Strip Path**: `off`
   - **Tags**: `a2a`
3. Click **Save** *(no plugins - this route is intentionally public so any
   client can discover what skills the orchestrator offers)*

### 6.4 Create the Flights Sub-Agent Route + Plugins

1. New Route on `a2a-backend`:
   - **Name**: `a2a-flights`
   - **Path(s)**: `/a2a/flights`
   - **Method(s)**: `POST`
   - **Strip Path**: `off`
   - **Tags**: `a2a`
2. Click **Save**, then add **New Plugin → Authentication → Key Authentication**:
   - **Key Names**: `X-Agent-Key`
   - **Hide Credentials**: `on`
3. Click **Save**, then add **New Plugin → Traffic Control → Rate Limiting**:
   - **Minute**: `30`
   - **Policy**: `local`
4. Click **Save**

### 6.5 Create the Hotels Sub-Agent Route + Plugins

1. New Route on `a2a-backend`:
   - **Name**: `a2a-hotels`
   - **Path(s)**: `/a2a/hotels`
   - **Method(s)**: `POST`
   - **Strip Path**: `off`
   - **Tags**: `a2a`
2. Click **Save**, then add **New Plugin → Authentication → Key Authentication**:
   - **Key Names**: `X-Agent-Key`
   - **Hide Credentials**: `on`
3. Click **Save**, then add **New Plugin → Traffic Control → Rate Limiting**:
   - **Minute**: `30`
   - **Policy**: `local`
4. Click **Save**

### 6.6 Create the Weather Sub-Agent Route + Plugin

1. New Route on `a2a-backend`:
   - **Name**: `a2a-weather`
   - **Path(s)**: `/a2a/weather`
   - **Method(s)**: `POST`
   - **Strip Path**: `off`
   - **Tags**: `a2a`
2. Click **Save**, then add **New Plugin → Traffic Control → Rate Limiting**:
   - **Minute**: `60`
   - **Policy**: `local`
3. Click **Save** *(no key-auth - weather is a low-trust, high-volume read)*

### 6.7 Test - Agent Card discovery

```bash
curl -s $PROXY_URL/.well-known/agent.json | jq '{name: .name, skills: [.skills[].id]}'
```

**Expected:** `{"name": "TravelOrchestratorAgent", "skills": ["flight-search","hotel-booking","weather-check"]}`

### 6.8 Test - No key → 401

```bash
curl -si -X POST $PROXY_URL/a2a/flights \
  -H "Content-Type: application/json" \
  -d '{"id":"t1","message":{"role":"user","parts":[{"type":"text","text":"SFO to LHR"}]}}' \
  | head -1
```

**Expected:** `HTTP/1.1 401 Unauthorized`

### 6.9 Test - With key → 200

```bash
curl -s -X POST $PROXY_URL/a2a/flights \
  -H "X-Agent-Key: orchestrator-key-xyz" \
  -H "Content-Type: application/json" \
  -d '{"id":"t1","message":{"role":"user","parts":[{"type":"text","text":"SFO to LHR June 15"}]}}' \
  | jq '.result.parts[0].text | fromjson | .[0]'
```

**Expected:** Flight object with `airline`, `price`, `departure`.

### 6.10 Test - Weather (no auth, different rate limit)

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

### 6.11 Test - Full A2A delegation

```bash
# Flights
curl -s -X POST $PROXY_URL/a2a/flights \
  -H "X-Agent-Key: orchestrator-key-xyz" \
  -H "Content-Type: application/json" \
  -d '{"id":"task-001","message":{"role":"user","parts":[{"type":"text","text":"Round-trip SFO to LHR June 15-22"}]}}' \
  | jq '.result.parts[0].text | fromjson | .[0]'

# Hotels (use airport code LHR - backend matches on 3-letter codes)
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

## Cleanup

1. Go to **Gateway Manager → `<your-control-plane>` → Services**
2. Delete each service (cascades to routes + plugins):
   - `mcp-backend`
   - `httpbun-service`
   - `mcp-backend-oauth`
   - `a2a-backend`
3. Go to **Consumers** and delete:
   - `mcp-user`
   - `orchestrator-agent`
4. Stop the Docker services and ngrok:
   ```bash
   cd 05-mcp-a2a
   docker compose down -v        # stops the MCP backend
   # Stop ngrok (Ctrl+C in the ngrok terminal)
   ```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `502 Bad Gateway` for MCP backend calls | Check ngrok tunnel is running and the hostname in the service matches |
| ngrok tunnel shows `ERR_NGROK_...` | Free tier allows 1 tunnel at a time. Stop other tunnels first |
| Step 3/4 tool calls return 404 | Tool `path` must match an existing Kong route (e.g. `/httpbun/ip` → `httpbun-route`) |
| Step 4 aggregate sees 0 tools | Each `conversion-only` plugin must carry the **plugin-level** tag `mcp-agg`, not just the route tag |
| OAuth2 returns 401 with valid token | Check **JWKS Endpoint** uses `https://<AUTH0_DOMAIN>/.well-known/jwks.json` |
| OAuth2 returns 401 with audience error | Confirm **Insecure Relaxed Audience Validation** is `on` for the lab, or pass the correct `audience` when requesting the token |
| A2A hotels returns empty results | Use 3-letter airport codes (LHR, CDG) - backend matches on `location === code` |
| Plugin not visible in UI | Ensure your Kong Gateway version is 3.14+ with AI plugins enabled |
