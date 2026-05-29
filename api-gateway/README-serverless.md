# Kong API Gateway Bootcamp — Konnect Serverless

> **Deployment:** Konnect Control Plane + Konnect Serverless Data Plane
> No Docker required. All infrastructure managed by Kong.

---

## Prerequisites

- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- [Insomnia](https://insomnia.rest/) installed
- Konnect account with a control plane (serverless DP auto-provisioned)

## Environment Setup

```bash
export KONNECT_TOKEN=<your-personal-access-token>
export CP_NAME=TCS-Bootcamp
export PROXY_URL=https://<your-serverless-dp-id>.us.serverless.gateways.konggateway.com
```

> Get your serverless proxy URL from: **Gateway Manager → TCS-Bootcamp → Overview → Proxy URL**

---

## Architecture

```
┌──────────────┐       ┌──────────────────────┐       ┌──────────────┐
│   Client     │──────▶│  Konnect Serverless   │──────▶│  httpbin.org │
│  (curl /     │       │  Data Plane           │       │  httpbun.com │
│   Insomnia)  │       │  (managed by Kong)    │       │  httpbin.    │
│              │       │                       │       │  konghq.com  │
└──────────────┘       └──────────────────────┘       └──────────────┘
                              ▲
                              │ Config sync
                       ┌──────┴──────┐
                       │   Konnect   │
                       │   Control   │◀──── deck gateway sync/apply
                       │   Plane     │
                       └─────────────┘
```

---

## File Structure

```
api-gateway/
├── deck/
│   ├── 01-services-and-routes.yaml   ← Base: 3 services + 3 routes
│   ├── 02-rate-limiting.yaml         ← Rate Limiting (httpbin, 5 req/min)
│   ├── 03-proxy-cache.yaml           ← Proxy Cache (30s TTL, memory)
│   ├── 04-upstream.yaml              ← Load Balancing (round-robin)
│   ├── 05-key-auth.yaml              ← Key Auth + consumers
│   ├── 06-jwt-auth.yaml              ← JWT Auth + consumer
│   ├── 07-consumers.yaml             ← Multiple consumers
│   ├── 08-cors.yaml                  ← CORS (global)
│   ├── 09-ip-restriction.yaml        ← IP Restriction (httpbin)
│   ├── 10-correlation-id.yaml        ← Correlation ID (global)
│   ├── 11-request-transformer.yaml   ← Request Transformer (httpbin)
│   ├── 12-response-transformer.yaml  ← Response Transformer (httpbin)
│   ├── 13-http-log.yaml              ← HTTP Log (httpbin)
│   └── 14-consumer-groups-acl.yaml   ← Consumer Groups + ACL
├── insomnia/
│   └── kong-gateway-bootcamp.json    ← Full Insomnia collection
├── README-serverless.md              ← This file
└── README-hybrid.md                  ← Docker hybrid deployment guide
```

## Backends

| Service | Backend | Protocol | Port | Notes |
|---------|---------|----------|------|-------|
| httpbin-service | httpbin.org | HTTPS | 443 | Most popular HTTP echo service |
| httpbun-service | httpbun.com | HTTPS | 443 | Reliable alternative |
| konghq-service | httpbin.konghq.com | HTTP | 80 | Kong-hosted (HTTP only) |

## Routes

| Route | Path | Maps To |
|-------|------|---------|
| httpbin-route | `/httpbin/*` | httpbin.org/* |
| httpbun-route | `/httpbun/*` | httpbun.com/* |
| konghq-route | `/konghq/*` | httpbin.konghq.com/* |

All routes use `strip_path: true` — the prefix is removed before forwarding.

---

## Quick Start

### Step 1 — Verify Serverless DP is Active

```bash
# Check your proxy URL is reachable
curl -s $PROXY_URL | jq .message
# → "no Route matched with those values" (expected — no routes configured yet)
```

> If you don't have a serverless DP, create one in Konnect:
> **Gateway Manager → New Control Plane → Serverless**

### Step 2 — Apply Base Services & Routes

```bash
deck gateway sync \
  deck/01-services-and-routes.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

### Step 3 — Verify

```bash
curl -s $PROXY_URL/httpbin/get | jq .origin
curl -s $PROXY_URL/httpbun/get | jq .url
curl -s $PROXY_URL/konghq/get | jq .origin
```

### Step 4 — Import Insomnia Collection

Open Insomnia → Import → select `insomnia/kong-gateway-bootcamp.json`
Switch environment to **"Konnect Serverless DP"**.

---

## Serverless-Specific Notes

| Topic | Detail |
|-------|--------|
| **PROXY_URL** | `https://<id>.us.serverless.gateways.konggateway.com` (HTTPS only) |
| **No Docker needed** | DP is fully managed by Kong — zero infrastructure |
| **Config propagation** | ~5-10 seconds after `deck gateway apply/sync` |
| **httpbin.konghq.com** | ⚠️ May be unreachable from serverless DP (DNS/HTTP-only issues). Use httpbin.org or httpbun.com instead |
| **HTTP Log plugin** | ⚠️ `host.docker.internal` won't work — you need a publicly reachable log endpoint (e.g., webhook.site, requestbin.com, or your own server) |
| **IP Restriction** | Client IP seen by Kong is the CDN/edge IP, not your local machine IP |

### HTTP Log Alternative for Serverless

Replace `host.docker.internal:9999` with a public endpoint:

```bash
# Get a free temporary endpoint
# Visit https://webhook.site — copy your unique URL
# Update 13-http-log.yaml: http_endpoint → your webhook.site URL
```

---

## Plugin Demos

### How to Apply a Plugin

```bash
deck gateway apply \
  deck/<plugin-file>.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

### How to Clean Up Between Demos

Re-sync the base file to remove all plugins and extra entities:

```bash
deck gateway sync \
  deck/01-services-and-routes.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

---

## Plugin-by-Plugin Guide

### 02 — Rate Limiting

Limits httpbin-service to **5 requests/minute** per IP.

```bash
deck gateway apply deck/02-rate-limiting.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# First 5 calls → 200 with rate limit headers
curl -i $PROXY_URL/httpbin/get
# Headers: X-RateLimit-Limit-Minute: 5, X-RateLimit-Remaining-Minute: 4

# 6th call → 429 Too Many Requests
curl -i $PROXY_URL/httpbin/get

# httpbun is NOT rate limited
curl -i $PROXY_URL/httpbun/get
```

---

### 03 — Proxy Cache

Caches GET 200 responses from httpbin-service for **30 seconds** in memory.

```bash
deck gateway apply deck/03-proxy-cache.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# First call → X-Cache-Status: Miss
curl -i $PROXY_URL/httpbin/get

# Second call (within 30s) → X-Cache-Status: Hit
curl -i $PROXY_URL/httpbin/get

# POST → X-Cache-Status: Bypass (POST not cached)
curl -i -X POST $PROXY_URL/httpbin/post -d '{}'
```

---

### 04 — Upstream / Load Balancing

Round-robin across httpbin.org and httpbun.com via `/lb` route.

```bash
deck gateway apply deck/04-upstream.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# Run multiple times — observe different backends
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
```

---

### 05 — Key Auth

Protects httpbin-service with API key authentication.

```bash
deck gateway apply deck/05-key-auth.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# No key → 401
curl -i $PROXY_URL/httpbin/get

# Key in header → 200
curl -i $PROXY_URL/httpbin/get -H "apikey: my-secret-key-123"

# Key in query → 200
curl -i "$PROXY_URL/httpbin/get?apikey=my-secret-key-123"

# Wrong key → 401
curl -i $PROXY_URL/httpbin/get -H "apikey: wrong-key"

# httpbun is open (no key-auth)
curl -i $PROXY_URL/httpbun/get
```

**Consumers:** `demo-user` (my-secret-key-123), `test-user` (test-key-456)

---

### 06 — JWT Auth

Protects httpbun-service with JWT token authentication.

```bash
deck gateway apply deck/06-jwt-auth.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

Generate a JWT token:

```bash
pip3 install PyJWT  # one-time

TOKEN=$(python3 -c "
import jwt, time
token = jwt.encode(
    {'iss': 'my-jwt-issuer', 'exp': int(time.time()) + 3600},
    'my-super-secret-key',
    algorithm='HS256'
)
print(token)
")
echo $TOKEN
```

```bash
# No token → 401
curl -i $PROXY_URL/httpbun/get

# With JWT → 200
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"
```

---

### 07 — Consumers

Creates multiple consumers with API keys. **Requires key-auth plugin** (apply 05 first).

```bash
deck gateway apply deck/05-key-auth.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
deck gateway apply deck/07-consumers.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
curl -s $PROXY_URL/httpbin/get -H "apikey: alice-api-key"   # X-Consumer-Username: alice
curl -s $PROXY_URL/httpbin/get -H "apikey: bob-api-key"     # X-Consumer-Username: bob
curl -s $PROXY_URL/httpbin/get -H "apikey: charlie-api-key" # X-Consumer-Username: charlie
```

---

### 08 — CORS

Global CORS plugin — allows cross-origin requests from specified origins.

```bash
deck gateway apply deck/08-cors.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# Simple request with Origin
curl -i $PROXY_URL/httpbin/get -H "Origin: http://localhost:3000"
# → Access-Control-Allow-Origin: http://localhost:3000

# Preflight request
curl -i -X OPTIONS $PROXY_URL/httpbin/get \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

---

### 09 — IP Restriction

Allows only specified IPs to access httpbin-service.

```bash
deck gateway apply deck/09-ip-restriction.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

> ⚠️ **Serverless note:** The client IP seen by Kong is the edge/CDN IP, not your local IP. You may need to adjust the allow list or test from a known IP range.

```bash
curl -i $PROXY_URL/httpbin/get
```

---

### 10 — Correlation ID

Adds a unique `X-Correlation-ID` header to every request (global).

```bash
deck gateway apply deck/10-correlation-id.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# Check response header
curl -i $PROXY_URL/httpbin/get
# → X-Correlation-ID: uuid#1

# Check upstream received it
curl -s $PROXY_URL/httpbin/headers | jq '.headers["X-Correlation-Id"]'

# Send your own ID
curl -i $PROXY_URL/httpbin/get -H "X-Correlation-ID: my-trace-123"
```

---

### 11 — Request Transformer

Adds headers and query params to requests before they reach httpbin upstream.

```bash
deck gateway apply deck/11-request-transformer.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# See added headers
curl -s $PROXY_URL/httpbin/headers | jq '.headers'
# → "X-Added-By": "Kong-Gateway", "X-Bootcamp": "API-Gateway-Demo"

# See added query params
curl -s $PROXY_URL/httpbin/get | jq '.args'
# → "source": "kong", "gateway": "true"
```

---

### 12 — Response Transformer

Adds/removes response headers before they reach the client.

```bash
deck gateway apply deck/12-response-transformer.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
curl -i $PROXY_URL/httpbin/get
# Added:   X-Powered-By: Kong-Gateway, X-Bootcamp-Demo: true
# Removed: Server, Via
```

---

### 13 — HTTP Log

Sends request/response logs to an HTTP endpoint.

```bash
deck gateway apply deck/13-http-log.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
curl -s $PROXY_URL/httpbin/get
# → Check your webhook.site dashboard for the logged JSON payload
```

> The plugin POSTs logs to the configured [webhook.site](https://webhook.site) URL. Open it in a browser to see logs in real time.
> To change the endpoint, edit `deck/13-http-log.yaml` → `http_endpoint`.

---

### 14 — Consumer Groups + ACL

Combines **Key Auth** (authentication), **ACL** (authorization), and **Consumer Groups** (tiered rate limiting).

```bash
deck gateway apply deck/14-consumer-groups-acl.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# No key → 401
curl -i $PROXY_URL/httpbin/get

# Premium → 200, 1000 req/min
curl -i $PROXY_URL/httpbin/get -H "apikey: premium-key-123"

# Standard → 200, 10 req/min
curl -i $PROXY_URL/httpbin/get -H "apikey: standard-key-456"

# Trial → 403 (authenticated but blocked by ACL)
curl -i $PROXY_URL/httpbin/get -H "apikey: blocked-key-789"
```

| Consumer | API Key | ACL Group | Consumer Group | Rate Limit | Access |
|----------|---------|-----------|----------------|------------|--------|
| premium-user | `premium-key-123` | premium | premium-tier | 1000/min | ✅ Allowed |
| standard-user | `standard-key-456` | standard | standard-tier | 10/min | ✅ Allowed |
| trial-user | `blocked-key-789` | trial | _(none)_ | — | ❌ Denied (403) |

> See [README-hybrid.md](README-hybrid.md#14--consumer-groups--acl) for the full step-by-step walkthrough, request flow diagram, and Konnect UI verification steps.

---

## Insomnia Collection

Import `insomnia/kong-gateway-bootcamp.json` into Insomnia.

Switch to **"Konnect Serverless DP"** environment → sets `base_url` to your serverless proxy URL.

For JWT tests: generate a token, then set `jwt_token` in the Insomnia environment.

---

## Full Reset

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force
```

---

## Useful httpbin/httpbun Paths

| Path | Method | What It Does |
|------|--------|-------------|
| `/get` | GET | Echo query params, headers, origin |
| `/post` | POST | Echo POST body and headers |
| `/headers` | GET | Show all request headers |
| `/ip` | GET | Show client IP |
| `/anything` | ANY | Echo everything |
| `/delay/N` | GET | Respond after N seconds |
| `/status/CODE` | ANY | Return specific HTTP status code |
| `/response-headers?key=val` | GET | Set custom response headers |
