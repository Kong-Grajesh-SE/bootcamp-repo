# Kong API Gateway Bootcamp - Konnect Hybrid (Docker DP)

> **Deployment:** Konnect Control Plane + Self-Managed Docker Data Plane
> Config managed in Konnect via decK. Traffic processed by a local Docker container.

---

## Prerequisites

- Docker Desktop running
- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- [Insomnia](https://insomnia.rest/) installed
- Konnect account with a control plane

## Environment Setup

```bash
export KONNECT_TOKEN=<your-personal-access-token>
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=http://localhost:8000
```

---

## Architecture

```
┌──────────────┐       ┌──────────────────────┐       ┌──────────────┐
│   Client     │──────▶│  Docker Data Plane    │──────▶│  httpbin.org │
│  (curl /     │       │  (localhost:8000)     │       │  httpbun.com │
│   Insomnia)  │       │  kong/kong-gateway:3.9│       │  httpbin.    │
│              │       │                       │       │  konghq.com  │
└──────────────┘       └──────────────────────┘       └──────────────┘
                              ▲
                              │ mTLS config sync
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
│   ├── 14-consumer-groups-acl.yaml   ← Consumer Groups + ACL
│   ├── 15-kong-identity.yaml         ← Kong Identity (Konnect-native M2M auth)
│   └── 16-oidc-keycloak.yaml         ← OpenID Connect via local Keycloak (AuthN/AuthZ)
├── insomnia/
│   └── kong-gateway-bootcamp.json    ← Full Insomnia collection
├── README-serverless.md              ← Konnect Serverless guide
└── README-hybrid.md                  ← This file
```

> **Keycloak for step 16 is shared** across all bootcamp modules - it lives at
> the repo root in [`../../keycloak/`](../../keycloak/) (realm `bootcamp`).

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

All routes use `strip_path: true` - the prefix is removed before forwarding.

---

## Quick Start


> Replace `<your-control-plane>` with the value you set in `$CP_NAME`.


### Step 3 - Verify DP is Connected

```bash
# Check container is running
docker ps --filter name=upbeat_yonath

# Check DP logs for successful connection
docker logs upbeat_yonath 2>&1 | tail -20

# Look for: "successfully connected to the control plane"
```

In Konnect UI: **Gateway Manager → your-control-plane → Data Plane Nodes** - should show your node as connected.

```bash
# Test the proxy (will return 404 - no routes configured yet)
curl -s $PROXY_URL | jq .message
# → "no Route matched with those values"
```

### Step 4 - Apply Base Services & Routes

```bash
deck gateway sync \
  deck/01-services-and-routes.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

### Step 5 - Verify Routes

```bash
curl -s $PROXY_URL/httpbin/get | jq .origin
curl -s $PROXY_URL/httpbun/get | jq .url
curl -s $PROXY_URL/konghq/get | jq .origin
```

### Step 6 - Import Insomnia Collection

Open Insomnia → Import → select `insomnia/kong-gateway-bootcamp.json`
Switch environment to **"Docker DP (localhost:8000)"** (default).

---

## Docker DP Management

### Start / Stop / Restart

```bash
# Stop the data plane
docker stop upbeat_yonath

# Start it again
docker start upbeat_yonath

# Restart
docker restart upbeat_yonath

# View logs (live)
docker logs -f upbeat_yonath
```

### Remove and Recreate

```bash
docker rm -f upbeat_yonath
# Then re-run the docker run command from Step 2
```

### Check DP Health

```bash
# Kong status endpoint (inside the container)
docker exec upbeat_yonath kong health
```

---

## Hybrid-Specific Notes

| Topic | Detail |
|-------|--------|
| **PROXY_URL** | `http://localhost:8000` (HTTP) or `https://localhost:8443` (HTTPS, self-signed) |
| **Config propagation** | ~5 seconds after `deck gateway apply/sync` |
| **Client IP** | Docker bridge IP (`172.x.x.x`), not `127.0.0.1` - affects IP Restriction plugin |
| **host.docker.internal** | Resolves to your Mac/host machine - used by HTTP Log plugin |
| **httpbin.konghq.com** | HTTP-only (port 80) - works from Docker DP (unlike serverless) |
| **Certificates** | Must be saved in `certs/` and mounted into the container |

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

### 02 - Rate Limiting

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

### 03 - Proxy Cache

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

### 04 - Upstream / Load Balancing

Round-robin across httpbin.org and httpbun.com via `/lb` route.

```bash
deck gateway apply deck/04-upstream.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# Run multiple times - observe different backends
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
```

---

### 05 - Key Auth

Protects httpbin-service with API key authentication.

> **Consumer - quick primer (covered in depth in Step 07):** A **consumer**
> in Kong is an identity that Kong knows about - typically a person, a
> service account, or a partner. Credentials (API key, JWT secret, OAuth
> client) are attached to a consumer, so when Kong validates a credential
> it can tell you *who* called the route. The decK file below creates two
> consumers (`demo-user`, `test-user`) alongside the plugin so the demo is
> self-contained; Step 07 unpacks the standalone consumer concept and Step
> 14 ties it together with consumer groups and ACL.

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

### 06 - JWT Auth

Protects httpbun-service with JWT token authentication.

```bash
deck gateway apply deck/06-jwt-auth.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

First generate a random HS256 secret and substitute it into `deck/06-jwt-auth.yaml`
(replace the `<REPLACE-WITH-RANDOM-SECRET>` placeholder), then re-apply the file:

```bash
JWT_SECRET=$(openssl rand -hex 32)
sed -i.bak "s|<REPLACE-WITH-RANDOM-SECRET>|$JWT_SECRET|" deck/06-jwt-auth.yaml
deck gateway apply deck/06-jwt-auth.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

Generate a JWT token signed with that secret:

```bash
pip3 install PyJWT  # one-time

TOKEN=$(python3 -c "
import jwt, time, os
token = jwt.encode(
    {'iss': 'my-jwt-issuer', 'exp': int(time.time()) + 3600},
    os.environ['JWT_SECRET'],
    algorithm='HS256'
)
print(token if isinstance(token, str) else token.decode())
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

### 07 - Consumers

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

### 08 - CORS

Global CORS plugin - allows cross-origin requests from specified origins.

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

### 09 - IP Restriction

Allows only local/private IPs to access httpbin-service.

```bash
deck gateway apply deck/09-ip-restriction.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# From local machine via Docker → 200 (Docker bridge IP is in allow list)
curl -i $PROXY_URL/httpbin/get

# To test blocking: remove 172.16.0.0/12 from allow list, re-apply, then:
curl -i $PROXY_URL/httpbin/get
# → 403 "Your IP address is not allowed"
```

> **Docker note:** Your client IP appears as `172.x.x.x` (Docker bridge), not `127.0.0.1`. The allow list includes `172.16.0.0/12` (the RFC 1918 range Docker bridges live in) for this reason.

---

### 10 - Correlation ID

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

### 11 - Request Transformer

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

### 12 - Response Transformer

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

### 13 - HTTP Log

Sends request/response logs to an external HTTP endpoint ([webhook.site](https://webhook.site)).

```bash
deck gateway apply deck/13-http-log.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
curl -s $PROXY_URL/httpbin/get
# → Check your webhook.site dashboard for the logged JSON payload
```

> **How it works:** The plugin POSTs a JSON log entry to the configured webhook.site URL after every proxied request. Open your webhook.site unique URL in a browser to see logs appear in real time.
>
> To use your own endpoint, edit `deck/13-http-log.yaml` and change `http_endpoint`.
> For local Docker receivers, use `http://host.docker.internal:9999/log`.

---

### 14 - Consumer Groups + ACL

This demo combines **three Kong features** to build a tiered API access system:

1. **Key Auth** - identifies _who_ is making the request (authentication)
2. **ACL (Access Control List)** - decides _if_ they're allowed (authorization)
3. **Consumer Groups** - applies _different rate limits_ per tier (policy)

#### How It Works - Request Flow

```
Client sends request with API key
        │
        ▼
┌─────────────────┐
│  1. Key Auth    │  Looks up the API key → finds the consumer
│     Plugin      │  No key or wrong key → 401 Unauthorized
└────────┬────────┘
         │ Consumer identified (e.g., premium-user)
         ▼
┌─────────────────┐
│  2. ACL Plugin  │  Checks consumer's ACL group against allow list
│                 │  premium, standard → allowed
│                 │  trial → 403 Forbidden
└────────┬────────┘
         │ Consumer authorized
         ▼
┌─────────────────┐
│  3. Consumer    │  Applies group-specific rate limit
│     Group       │  premium-tier → 1000 req/min
│     Rate Limit  │  standard-tier → 10 req/min
└────────┬────────┘
         │
         ▼
    Request → upstream (httpbin)
```

#### What Gets Created

**Plugins (on httpbin-service):**
- `key-auth` - requires `apikey` header, hides credential from upstream
- `acl` - only allows consumers in `premium` or `standard` groups

**Consumers:**

| Consumer | API Key | ACL Group | Consumer Group | Rate Limit | Access |
|----------|---------|-----------|----------------|------------|--------|
| premium-user | `premium-key-123` | premium | premium-tier | 1000/min | ✅ Allowed |
| standard-user | `standard-key-456` | standard | standard-tier | 10/min | ✅ Allowed |
| trial-user | `blocked-key-789` | trial | _(none)_ | - | ❌ Denied (403) |

> **Key concept:** ACL group ≠ Consumer Group. They serve different purposes:
> - **ACL group** (e.g., `premium`) → used by the ACL plugin for authorization
> - **Consumer Group** (e.g., `premium-tier`) → used for group-scoped rate limiting
> - A consumer can belong to both independently

**Consumer Groups:**
- `premium-tier` - rate-limiting plugin override: 1000 req/min
- `standard-tier` - rate-limiting plugin override: 10 req/min

#### Step-by-Step Setup in Konnect UI

**Step 1 - Add Key Auth plugin to httpbin-service:**

```
Gateway Manager → your-control-plane → Services → httpbin-service → Plugins → Add Plugin
  → Authentication → Key Authentication
  → Config:
       Key Names: apikey
       Hide Credentials: enabled ✅
  → Scope: httpbin-service (already selected)
  → Save
```

**Step 2 - Add ACL plugin to httpbin-service:**

```
Gateway Manager → your-control-plane → Services → httpbin-service → Plugins → Add Plugin
  → Traffic Control → ACL
  → Config:
       Allow: premium, standard     ← only these groups can access
       Hide Groups Header: disabled
  → Save
```

**Step 3 - Create consumer: premium-user:**

```
Gateway Manager → your-control-plane → Consumers → New Consumer
  → Username: premium-user
  → Custom ID: premium-001
  → Save

  → Credentials tab → New Key Auth Credential
       Key: premium-key-123
       → Save

  → ACL tab → Add Group
       Group: premium
       → Save
```

**Step 4 - Create consumer: standard-user:**

```
Gateway Manager → your-control-plane → Consumers → New Consumer
  → Username: standard-user
  → Custom ID: standard-002
  → Save

  → Credentials tab → New Key Auth Credential
       Key: standard-key-456
       → Save

  → ACL tab → Add Group
       Group: standard
       → Save
```

**Step 5 - Create consumer: trial-user:**

```
Gateway Manager → your-control-plane → Consumers → New Consumer
  → Username: trial-user
  → Custom ID: trial-003
  → Save

  → Credentials tab → New Key Auth Credential
       Key: blocked-key-789
       → Save

  → ACL tab → Add Group
       Group: trial          ← NOT in the ACL allow list, so this user gets 403
       → Save
```

**Step 6 - Create consumer group: premium-tier:**

```
Gateway Manager → your-control-plane → Consumer Groups → New Consumer Group
  → Name: premium-tier
  → Save

  → Members tab → Add Consumer
       Select: premium-user → Add

  → Plugins tab → Add Plugin → Rate Limiting
       Minute: 1000
       Policy: local
       → Save
```

**Step 7 - Create consumer group: standard-tier:**

```
Gateway Manager → your-control-plane → Consumer Groups → New Consumer Group
  → Name: standard-tier
  → Save

  → Members tab → Add Consumer
       Select: standard-user → Add

  → Plugins tab → Add Plugin → Rate Limiting
       Minute: 10
       Policy: local
       → Save
```

**Step 8 - Verify the full setup:**

```
Gateway Manager → your-control-plane → Plugins
  → You should see: key-auth (httpbin-service), acl (httpbin-service)

Gateway Manager → your-control-plane → Consumers
  → 3 consumers listed: premium-user, standard-user, trial-user
  → Click premium-user → Credentials tab → Key: premium-key-123
  → Click premium-user → ACL tab → Group: premium
  → Click premium-user → Groups tab → Consumer Group: premium-tier

Gateway Manager → your-control-plane → Consumer Groups
  → premium-tier → 1 member, rate-limiting: 1000/min
  → standard-tier → 1 member, rate-limiting: 10/min
```

> **decK shortcut:** All of the above can be done in one command:
> ```bash
> deck gateway apply deck/14-consumer-groups-acl.yaml \
>   --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
> ```

> **Clean up:** Reset back to base services & routes (removes all plugins, consumers, consumer groups):
> ```bash
> deck gateway sync \
>   deck/01-services-and-routes.yaml \
>   --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
> ```



#### Test

```bash
# 1. No key → 401 Unauthorized
curl -i $PROXY_URL/httpbin/get

# 2. Premium user → 200, check rate limit headers
curl -i $PROXY_URL/httpbin/get -H "apikey: premium-key-123"
# → X-RateLimit-Limit-Minute: 1000
# → X-Consumer-Username: premium-user
# → X-Consumer-Groups: premium-tier

# 3. Standard user → 200, lower rate limit
curl -i $PROXY_URL/httpbin/get -H "apikey: standard-key-456"
# → X-RateLimit-Limit-Minute: 10
# → X-Consumer-Username: standard-user

# 4. Trial user → 403 Forbidden (authenticated but NOT authorized)
curl -i $PROXY_URL/httpbin/get -H "apikey: blocked-key-789"
# → {"message":"You cannot consume this service"}
# Note: Key auth passes (it's a valid key), but ACL blocks (trial not in allow list)

# 5. httpbun is unaffected (plugins scoped to httpbin-service only)
curl -i $PROXY_URL/httpbun/get
# → 200 (no auth needed)
```

#### Real-World Use Case

This pattern maps directly to SaaS API tiers:

| Tier | What they get | Maps to |
|------|--------------|--------|
| **Free** | Authenticated but blocked from premium endpoints | trial-user (ACL denied) |
| **Standard** | Access with modest rate limits | standard-user (10 req/min) |
| **Enterprise** | Access with high rate limits | premium-user (1000 req/min) |

In production, you'd combine this with Dev Portal App Registration so consumers and credentials are auto-provisioned when users subscribe to a plan.

---

### 15 - Kong Identity (Konnect-native M2M)

Steps 05 (key-auth) and 06 (JWT) used credentials Kong stores itself. The next
step up is delegating identity to an **OAuth2 / OpenID Connect** provider - and
the simplest place to start is **Kong Identity**
([developer.konghq.com/identity](https://developer.konghq.com/identity/)), a
**regional OAuth2 / OIDC authorization server hosted inside Konnect**. You get
machine-to-machine auth **without running any IdP yourself**: create an auth
server + client in Konnect, services mint tokens via `client_credentials`, and
the `openid-connect` plugin validates them. (Step 16 then swaps in a full
external IdP, Keycloak, for browser SSO.)

| | Kong Identity (this step) | Keycloak (step 16) |
|---|---|---|
| Where the IdP runs | Konnect-hosted, regional | You host it (Docker/ngrok) |
| Best for | Service-to-service (M2M) tokens | Browser SSO + user login |
| Setup | Konnect UI: Auth Server + Client | Docker Compose + realm |

#### Step 1 - Create the auth server + client in Konnect

```
Konnect → Identity → Auth Servers → New
  → pick your region → Save → copy the Issuer URL
Konnect → Identity → Clients → New
  → Grant: client_credentials → add a scope (e.g. api:read)
  → Save → copy client_id + client_secret
```

#### Step 2 - Fill in and apply the plugin

Edit `deck/15-kong-identity.yaml` and replace the three placeholders
(`issuer`, `client_id`, `client_secret`) with the values from above, then:

```bash
deck gateway apply deck/15-kong-identity.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

#### Step 3 - Test the M2M flow

```bash
ISSUER=<your-kong-identity-issuer-url>
CID=<your-client-id>
CSECRET=<your-client-secret>

# 1. Service obtains a token from Kong Identity
TOKEN=$(curl -s -X POST "$ISSUER/oauth2/token" \
  -d 'grant_type=client_credentials' \
  -d "client_id=$CID" -d "client_secret=$CSECRET" \
  | jq -r .access_token)

# 2. Call Kong with that token → 200
curl -i $PROXY_URL/httpbin/get -H "Authorization: Bearer $TOKEN"

# 3. No token → 401
curl -i $PROXY_URL/httpbin/get
```

> The exact `/oauth2/token` path is shown on your auth server's page in Konnect
> (read it from `<issuer>/.well-known/openid-configuration` → `token_endpoint`).

> **Clean up:** `deck gateway sync deck/01-services-and-routes.yaml …`.

---

### 16 - OIDC with Keycloak (Authentication / Authorization)

Kong Identity (step 15) is Konnect-hosted. When you instead need to integrate
your **own corporate IdP** - Okta, Entra ID, Auth0, Ping, or Keycloak - you point
the same **`openid-connect`** plugin at that external provider. Here you protect
`httpbun-service` with a local **Keycloak** acting as the OAuth2 / OIDC provider,
which also unlocks the **browser SSO (Authorization Code)** flow with real users.

```
┌────────┐  1. login / get token   ┌──────────────┐
│ Client │ ───────────────────────▶│   Keycloak   │  realm: bootcamp
│ (curl/ │ ◀───────────────────────│  :8080 (IdP) │  users: alice, bob-admin
│ browser)│      access token       └──────────────┘
│        │                                 ▲ 3. validate token (JWKS / discovery)
│        │  2. Bearer <token>      ┌────────┴───────┐
│        │ ───────────────────────▶│  Kong DP :8000  │ openid-connect plugin
└────────┘ ◀───────────────────────│  → httpbun.com  │ on httpbun-service
              4. 200 (or 401)       └────────────────┘
```

> Mirrors the enterprise OIDC lab from
> [learn-kong-gateway / module-07-enterprise](https://github.com/Kong-Grajesh-SE/learn-kong-gateway/tree/main/module-07-enterprise).

**Pre-built realm identities** (`../keycloak/realm-bootcamp.json`):

| Username | Password | Realm role | Group |
|---|---|---|---|
| `alice` | `alice-password` | `user` | `travel-users` |
| `bob-admin` | `bob-password` | `admin` | `platform-engineers` |

| Client | Type | Grants enabled |
|---|---|---|
| `kong` | confidential | authorization_code · password · client_credentials |
| `kong-m2m` | confidential | client_credentials |

> ⚠️ The client secrets in `../keycloak/realm-bootcamp.json` are committed for convenience.
> **Never** reuse them in production - generate real secrets in a vault.

> ⚠️ **Issuer must match - one hostname for host *and* container.** The Kong DP
> (a container) can only reach Keycloak at `host.docker.internal:8080`, so its
> issuer is `http://host.docker.internal:8080/realms/bootcamp`. OpenID Connect
> rejects a token whose `iss` claim doesn't equal that issuer - so you must mint
> tokens against the **same** host. Make your host resolve it (one-time):
> ```bash
> echo "127.0.0.1 host.docker.internal" | sudo tee -a /etc/hosts
> ```
> (Docker Desktop already resolves `host.docker.internal` inside containers;
> this adds it on the host so curl/browser use the identical issuer. On native
> Linux, also start the DP with `--add-host=host.docker.internal:host-gateway`.)

#### Step 1 - Start Keycloak

```bash
cd ../keycloak && docker compose up -d && cd -

# Wait for it to boot, then confirm the issuer is live (via the shared host):
curl -s http://host.docker.internal:8080/realms/bootcamp/.well-known/openid-configuration | jq .issuer
# → "http://host.docker.internal:8080/realms/bootcamp"
```

Admin Console: http://localhost:8080 (`admin` / `admin`).

#### Step 2 - Apply the openid-connect plugin

The Docker DP reaches Keycloak on your host via `host.docker.internal:8080`
(already set as the `issuer` in the deck file).

```bash
deck gateway apply deck/16-oidc-keycloak.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

#### Step 3 - Test (token via password grant)

```bash
# 1. No token → 401
curl -i $PROXY_URL/httpbun/get

# 2. Get an access token for alice - mint it against host.docker.internal so the
#    token's `iss` matches the issuer Kong validates against (see note above).
TOKEN=$(curl -s -X POST \
  -d 'grant_type=password' \
  -d 'client_id=kong' \
  -d 'client_secret=kong-bootcamp-client-secret-replace-in-prod' \
  -d 'username=alice' -d 'password=alice-password' \
  -d 'scope=openid profile email' \
  http://host.docker.internal:8080/realms/bootcamp/protocol/openid-connect/token \
  | jq -r .access_token)
echo "${TOKEN:0:40}…"

# 3. Call Kong with the bearer token → 200
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"
# Upstream also sees x-authenticated-user: alice / x-authenticated-email

# 4. Garbage token → 401
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer not-a-real-token"
```

#### Step 4 (optional) - Full browser login (Authorization Code flow)

Edit `deck/16-oidc-keycloak.yaml`, switch the plugin to the interactive flow,
then re-apply:

```yaml
    auth_methods: [authorization_code, bearer, session]
    login_action: redirect
```

Open `http://localhost:8000/httpbun/get` in a browser → Kong redirects to the
Keycloak login page → sign in as **alice / alice-password** → Keycloak redirects
back, Kong sets a session cookie and returns the upstream response.

> Revert to `login_action: response` and the password/bearer `auth_methods`
> before re-running the curl tests above.

> **Clean up:** `deck gateway sync deck/01-services-and-routes.yaml …` removes
> the plugin; `cd ../keycloak && docker compose down -v` stops Keycloak.

---

## Insomnia Collection

Import `insomnia/kong-gateway-bootcamp.json` into Insomnia.

Use **"Docker DP (localhost:8000)"** environment (selected by default).

For JWT tests: generate a token, then set `jwt_token` in the Insomnia environment.

---

## Full Reset

### Remove All Kong Config

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force
```

### Remove Docker DP

```bash
docker rm -f upbeat_yonath
```

### Clean Restart

```bash
docker rm -f upbeat_yonath
deck gateway reset --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME" --force
# Then re-run docker run + deck gateway sync from Quick Start
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `curl: (7) Failed to connect to localhost port 8000` | Docker container not running | `docker start upbeat_yonath` or re-run `docker run` |
| DP not showing in Konnect UI | Certs wrong or CP endpoint typo | Check `docker logs upbeat_yonath`, verify certs and endpoint |
| `no Route matched` after apply | Config not synced yet | Wait 5s and retry, or `docker restart upbeat_yonath` |
| 503 on `/konghq/*` | httpbin.konghq.com unreachable | Try `/httpbin/*` or `/httpbun/*` instead |
| IP Restriction blocking everything | Docker bridge IP not in allow list | Add `172.16.0.0/12` (the RFC 1918 range Docker bridges use) to the allow list |
| HTTP Log not receiving | Python server not running or wrong port | Check `python3` is listening on 9999, check `host.docker.internal` resolves |

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
