# Kong API Gateway Bootcamp - Konnect Serverless

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
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=https://<your-serverless-dp-id>.us.serverless.gateways.konggateway.com
```

> Get your serverless proxy URL from: **Gateway Manager → your CP → Overview → Proxy URL**

---

## Architecture

```
┌──────────────┐       ┌──────────────────────┐       ┌──────────────┐
│   Client     │──────▶│  Konnect Serverless   │──────▶│  httpbun.com │
│  (curl /     │       │  Data Plane           │       └──────────────┘
│   Insomnia)  │       │  (managed by Kong)    │
└──────────────┘       └──────────────────────┘
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
│   ├── 01-services-and-routes.yaml   ← Base: 1 service + 1 route (httpbun.com)
│   ├── 02-rate-limiting.yaml         ← Rate Limiting (httpbun, 5 req/min)
│   ├── 03-proxy-cache.yaml           ← Proxy Cache (30s TTL, memory)
│   ├── 04-upstream.yaml              ← Load Balancing (round-robin)
│   ├── 05-key-auth.yaml              ← Key Auth + consumers
│   ├── 06-jwt-auth.yaml              ← JWT Auth + consumer
│   ├── 07-consumers.yaml             ← Multiple consumers
│   ├── 08-cors.yaml                  ← CORS (global)
│   ├── 09-ip-restriction.yaml        ← IP Restriction (httpbun)
│   ├── 10-correlation-id.yaml        ← Correlation ID (global)
│   ├── 11-request-transformer.yaml   ← Request Transformer (httpbun)
│   ├── 12-response-transformer.yaml  ← Response Transformer (httpbun)
│   ├── 13-http-log.yaml              ← HTTP Log (httpbun)
│   ├── 14-consumer-groups-acl.yaml   ← Consumer Groups + ACL
│   ├── 15-kong-identity.yaml         ← Kong Identity (Konnect-native M2M auth)
│   ├── 16-oidc-keycloak.yaml         ← OpenID Connect via Keycloak (generic)
│   ├── 16-oidc-keycloak-serverless.yaml  ← ↳ Serverless variant (ngrok issuer)
│   ├── 16-oidc-keycloak-hybrid.yaml      ← ↳ Hybrid variant (host.docker.internal)
│   ├── 16-oidc-introspection-serverless.yaml ← ↳ + Introspection (serverless)
│   ├── 16-oidc-introspection-hybrid.yaml     ← ↳ + Introspection (hybrid)
│   └── 17-upstream-oauth.yaml        ← Upstream OAuth (Kong → backend M2M token)
├── insomnia/
│   └── kong-gateway-bootcamp.json    ← Full Insomnia collection
├── README-serverless.md              ← This file
└── README-hybrid.md                  ← Docker hybrid deployment guide
```

> **Keycloak for step 16 is shared** across all bootcamp modules - it lives at
> the repo root in [`../../keycloak/`](../../keycloak/) (realm `bootcamp`).

## Backends

| Service | Backend | Protocol | Port | Notes |
|---------|---------|----------|------|-------|
| httpbun-service | httpbun.com | HTTPS | 443 | Reliable HTTP echo service |

## Routes

| Route | Path | Maps To |
|-------|------|---------|
| httpbun-route | `/httpbun/*` | httpbun.com/* |

All routes use `strip_path: true` - the prefix is removed before forwarding.

---

## Quick Start

### Step 1 - Verify Serverless DP is Active

```bash
# Check your proxy URL is reachable
curl -s $PROXY_URL | jq .message
# → "no Route matched with those values" (expected - no routes configured yet)
```

> If you don't have a serverless DP, create one in Konnect:
> **Gateway Manager → New Control Plane → Serverless**

### Step 2 - Apply Base Services & Routes

```bash
deck gateway sync \
  deck/01-services-and-routes.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

### Step 3 - Verify

```bash
curl -s $PROXY_URL/httpbun/get | jq .url
```

### Step 4 - Import Insomnia Collection

Open Insomnia → Import → select `insomnia/kong-gateway-bootcamp.json`
Switch environment to **"Konnect Serverless DP"**.

---

## Serverless-Specific Notes

| Topic | Detail |
|-------|--------|
| **PROXY_URL** | `https://<id>.us.serverless.gateways.konggateway.com` (HTTPS only) |
| **No Docker needed** | DP is fully managed by Kong - zero infrastructure |
| **Config propagation** | ~5-10 seconds after `deck gateway apply/sync` |
| **HTTP Log plugin** | ⚠️ `host.docker.internal` won't work - you need a publicly reachable log endpoint (e.g., webhook.site, requestbin.com, or your own server) |
| **IP Restriction** | Client IP seen by Kong is the CDN/edge IP, not your local machine IP |

### HTTP Log Alternative for Serverless

Replace `host.docker.internal:9999` with a public endpoint:

```bash
# Get a free temporary endpoint
# Visit https://webhook.site - copy your unique URL
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

### 02 - Rate Limiting

Limits httpbun-service to **5 requests/minute** per IP.

```bash
deck gateway apply deck/02-rate-limiting.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# First 5 calls → 200 with rate limit headers
curl -i $PROXY_URL/httpbun/get
# Headers: X-RateLimit-Limit-Minute: 5, X-RateLimit-Remaining-Minute: 4

# 6th call → 429 Too Many Requests
curl -i $PROXY_URL/httpbun/get
```

---

### 03 - Proxy Cache

Caches GET 200 responses from httpbun-service for **30 seconds** in memory.

```bash
deck gateway apply deck/03-proxy-cache.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# First call → X-Cache-Status: Miss
curl -i $PROXY_URL/httpbun/get

# Second call (within 30s) → X-Cache-Status: Hit
curl -i $PROXY_URL/httpbun/get

# POST → X-Cache-Status: Bypass (POST not cached)
curl -i -X POST $PROXY_URL/httpbun/post -d '{}'
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

Protects httpbun-service with API key authentication.

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
curl -i $PROXY_URL/httpbun/get

# Key in header → 200
curl -i $PROXY_URL/httpbun/get -H "apikey: my-secret-key-123"

# Key in query → 200
curl -i "$PROXY_URL/httpbun/get?apikey=my-secret-key-123"

# Wrong key → 401
curl -i $PROXY_URL/httpbun/get -H "apikey: wrong-key"
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
curl -s $PROXY_URL/httpbun/get -H "apikey: alice-api-key"   # X-Consumer-Username: alice
curl -s $PROXY_URL/httpbun/get -H "apikey: bob-api-key"     # X-Consumer-Username: bob
curl -s $PROXY_URL/httpbun/get -H "apikey: charlie-api-key" # X-Consumer-Username: charlie
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
curl -i $PROXY_URL/httpbun/get -H "Origin: http://localhost:3000"
# → Access-Control-Allow-Origin: http://localhost:3000

# Preflight request
curl -i -X OPTIONS $PROXY_URL/httpbun/get \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

---

### 09 - IP Restriction

Allows only specified IPs to access httpbun-service.

```bash
deck gateway apply deck/09-ip-restriction.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

> ⚠️ **Serverless note:** The client IP seen by Kong is the edge/CDN IP, not your local IP. You may need to adjust the allow list or test from a known IP range.

```bash
curl -i $PROXY_URL/httpbun/get
```

---

### 10 - Correlation ID

Adds a unique `X-Correlation-ID` header to every request (global).

```bash
deck gateway apply deck/10-correlation-id.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# Check response header
curl -i $PROXY_URL/httpbun/get
# → X-Correlation-ID: uuid#1

# Check upstream received it
curl -s $PROXY_URL/httpbun/headers | jq '.headers["X-Correlation-Id"]'

# Send your own ID
curl -i $PROXY_URL/httpbun/get -H "X-Correlation-ID: my-trace-123"
```

---

### 11 - Request Transformer

Adds headers and query params to requests before they reach httpbun upstream.

```bash
deck gateway apply deck/11-request-transformer.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
# See added headers
curl -s $PROXY_URL/httpbun/headers | jq '.headers'
# → "X-Added-By": "Kong-Gateway", "X-Bootcamp": "API-Gateway-Demo"

# See added query params
curl -s $PROXY_URL/httpbun/get | jq '.args'
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
curl -i $PROXY_URL/httpbun/get
# Added:   X-Powered-By: Kong-Gateway, X-Bootcamp-Demo: true
# Removed: X-Powered-By (upstream), Alt-Svc
#
# NOTE: Kong's own Server and Via headers are injected by Kong core AFTER
# plugins run — response-transformer cannot remove them.
```

---

### 13 - HTTP Log

Sends request/response logs to an HTTP endpoint.

```bash
deck gateway apply deck/13-http-log.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

```bash
curl -s $PROXY_URL/httpbun/get
# → Check your webhook.site dashboard for the logged JSON payload
```

> The plugin POSTs logs to the configured [webhook.site](https://webhook.site) URL. Open it in a browser to see logs in real time.
> To change the endpoint, edit `deck/13-http-log.yaml` → `http_endpoint`.

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
    Request → upstream (httpbun)
```

#### What Gets Created

**Plugins (on httpbun-service):**
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

#### Apply

```bash
deck gateway apply deck/14-consumer-groups-acl.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

#### Test

```bash
# 1. No key → 401 Unauthorized
curl -i $PROXY_URL/httpbun/get

# 2. Premium → 200, 1000 req/min budget
curl -i $PROXY_URL/httpbun/get -H "apikey: premium-key-123"

# 3. Standard → 200, 10 req/min budget
curl -i $PROXY_URL/httpbun/get -H "apikey: standard-key-456"

# 4. Trial → 403 (authenticated, but blocked by ACL because `trial` isn't in
#    the allow list)
curl -i $PROXY_URL/httpbun/get -H "apikey: blocked-key-789"

# 5. Watch the rate-limit headers on standard to confirm the group-scoped
#    policy is firing:
for i in 1 2 3; do
  curl -si $PROXY_URL/httpbun/get -H "apikey: standard-key-456" \
    | grep -i x-ratelimit
done
```

#### Konnect UI verification

```
Gateway Manager → <your-control-plane> → Plugins
  → You should see: key-auth (httpbun-service), acl (httpbun-service)

Gateway Manager → <your-control-plane> → Consumers
  → 3 consumers listed: premium-user, standard-user, trial-user
  → Click premium-user → Credentials tab → Key: premium-key-123
  → Click premium-user → ACL tab → Group: premium
  → Click premium-user → Groups tab → Consumer Group: premium-tier

Gateway Manager → <your-control-plane> → Consumer Groups
  → premium-tier → 1 member, rate-limiting: 1000/min
  → standard-tier → 1 member, rate-limiting: 10/min
```

> **Clean up:** Reset back to base service & routes (removes all plugins,
> consumers, and consumer groups created in this step):
> ```bash
> deck gateway sync \
>   deck/01-services-and-routes.yaml \
>   --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
> ```

---

### 15 - Kong Identity (Konnect-native M2M)

Steps 05 (key-auth) and 06 (JWT) used credentials Kong stores itself. The next
step up is delegating identity to an **OAuth2 / OpenID Connect** provider - and
the simplest place to start (especially on serverless) is **Kong Identity**
([developer.konghq.com/identity](https://developer.konghq.com/identity/)), a
**regional OAuth2 / OIDC authorization server hosted inside Konnect**. You get
machine-to-machine auth **without running (or tunnelling) any IdP at all**:
create an auth server + client in Konnect, services mint tokens via
`client_credentials`, and the `openid-connect` plugin validates them. (Step 16
then swaps in a full external IdP, Keycloak, for browser SSO.)

| | Kong Identity (this step) | Keycloak (step 16) |
|---|---|---|
| Where the IdP runs | Konnect-hosted, regional | You host it (+ ngrok for serverless) |
| Best for | Service-to-service (M2M) tokens | Browser SSO + user login |
| Serverless friction | None - already in Konnect | Needs a public tunnel |

#### Step 1 - Create the auth server + client in Konnect

```
Konnect → Identity → Auth Servers → New
  → pick your region → Save → copy the Issuer URL
Konnect → Identity → Clients → New
  → Grant: client_credentials → add a scope (e.g. api:read)
  → Save → copy client_id + client_secret
```

#### Step 2 - Fill in and apply the plugin

Edit `deck/15-kong-identity.yaml`, replace the `issuer`, `client_id`, and
`client_secret` placeholders, then:

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
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"

# 3. No token → 401
curl -i $PROXY_URL/httpbun/get
```

> Confirm the exact token endpoint from
> `<issuer>/.well-known/openid-configuration` → `token_endpoint`.

> **Clean up:** `deck gateway sync deck/01-services-and-routes.yaml …`.

---

### 16 - OIDC with Keycloak (Authentication / Authorization)

Kong Identity (step 15) is Konnect-hosted. When you instead need to integrate
your **own corporate IdP** - Okta, Entra ID, Auth0, Ping, or Keycloak - you point
the same **`openid-connect`** plugin at that external provider. Here you protect
`httpbun-service` with a **Keycloak** instance acting as the OAuth2 / OIDC
provider, which also unlocks the **browser SSO (Authorization Code)** flow with
real users.

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
> **Never** reuse them in production.

#### Serverless needs Keycloak to be *publicly reachable*

A serverless DP runs in Kong's cloud - it **cannot** reach `localhost:8080`.
Expose your local Keycloak with a tunnel so the DP can fetch discovery + JWKS,
and so the token `iss` claim matches what the plugin validates.

```bash
# 1. Start Keycloak locally
cd ../keycloak && docker compose up -d && cd -

# 2. Expose it publicly (ngrok free tier is fine)
ngrok http 8080
# → copy the https URL, e.g. https://9805-49-249-135-74.ngrok-free.app

# 3. Point Keycloak's frontendUrl at the ngrok URL so `iss` matches.
#    (Easiest: set KC_HOSTNAME on the container, or use the admin REST call
#    in ../keycloak/README.md.) Verify:
curl -s https://9805-49-249-135-74.ngrok-free.app/realms/bootcamp/.well-known/openid-configuration | jq .issuer
# → "https://9805-49-249-135-74.ngrok-free.app/realms/bootcamp"
```

The realm already pre-approves `https://*.kongcloud.dev/*` and
`https://*.us.serverless.gateways.konggateway.com/*` as redirect URIs, so the
browser flow works against your serverless proxy URL without extra Keycloak edits.

#### Apply the plugin (with the ngrok issuer)

Edit `deck/16-oidc-keycloak-serverless.yaml` — replace `<NGROK_URL>` with your
ngrok hostname and `<SERVERLESS_PROXY_URL>` with your serverless DP hostname:

```bash
# Quick sed replacements (or edit the file manually)
NGROK=abc123.ngrok-free.app          # your ngrok hostname
SL_PROXY=95fa62461d.us.serverless.gateways.konggateway.com  # your serverless DP

sed -i.bak \
  -e "s|<NGROK_URL>|$NGROK|g" \
  -e "s|<SERVERLESS_PROXY_URL>|$SL_PROXY|g" \
  deck/16-oidc-keycloak-serverless.yaml

deck gateway apply deck/16-oidc-keycloak-serverless.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

> **Hybrid deployment?** Use `deck/16-oidc-keycloak-hybrid.yaml` instead — no
> placeholders to replace, it uses `host.docker.internal:8080` as the issuer.

#### Test (token via password grant)

```bash
KC=https://9805-49-249-135-74.ngrok-free.app   # your ngrok URL

# 1. No token → 401
curl -i $PROXY_URL/httpbun/get

# 2. Get an access token for alice
TOKEN=$(curl -s -X POST \
  -H 'ngrok-skip-browser-warning: true' \
  -d 'grant_type=password' \
  -d 'client_id=kong' \
  -d 'client_secret=kong-bootcamp-client-secret-replace-in-prod' \
  -d 'username=alice' -d 'password=alice-password' \
  -d 'scope=openid profile email' \
  "$KC/realms/bootcamp/protocol/openid-connect/token" | jq -r .access_token)

# 3. Call Kong with the bearer token → 200
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"

# 4. Garbage token → 401
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer not-a-real-token"
```

> For the full browser Authorization Code flow, set
> `auth_methods: [authorization_code, bearer, session]` and
> `login_action: redirect` in the deck file, re-apply, then open your serverless
> proxy URL in a browser and sign in as **alice / alice-password**.

#### Token introspection (real-time revocation)

By default Kong validates the JWT **offline** against Keycloak's JWKS - fast, no
per-request call to the IdP, but a token stays valid until it expires even if the
user is logged out. **Introspection** ([RFC 7662](https://www.rfc-editor.org/rfc/rfc7662))
makes Kong call Keycloak's introspect endpoint on every request to ask "is this
token still active?", so revocation/logout takes effect immediately (and it also
works for opaque, non-JWT tokens).

| | Local JWKS validation (default) | Introspection |
|---|---|---|
| Per-request cost | None (verifies signature locally) | One call to Keycloak |
| Revocation honoured | Only at token expiry | Immediately |
| Works with opaque tokens | No (JWT only) | Yes |

> On serverless the introspect endpoint must be the **public ngrok URL** (the
> cloud DP reaches Keycloak over the internet, not `host.docker.internal`).

**See it directly** (reuse `$KC` and `$TOKEN` from the test above):

```bash
curl -s -u kong:kong-bootcamp-client-secret-replace-in-prod \
  -H 'ngrok-skip-browser-warning: true' \
  -d "token=$TOKEN" \
  "$KC/realms/bootcamp/protocol/openid-connect/token/introspect" | jq
# → { "active": true, "username": "alice", "scope": "openid profile email", ... }
```

**Switch the plugin to introspection** — use the dedicated introspection deck
file (replace `<NGROK_URL>` and `<SERVERLESS_PROXY_URL>` placeholders first):

```bash
sed -i.bak \
  -e "s|<NGROK_URL>|$NGROK|g" \
  -e "s|<SERVERLESS_PROXY_URL>|$SL_PROXY|g" \
  deck/16-oidc-introspection-serverless.yaml

deck gateway apply deck/16-oidc-introspection-serverless.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

> **Hybrid deployment?** Use `deck/16-oidc-introspection-hybrid.yaml` instead —
> no placeholders needed.

#### Deck file variants for Step 16

| Deck file | Deployment | Introspection | Issuer |
|---|---|---|---|
| `16-oidc-keycloak.yaml` | Generic (comments for both) | No | Placeholder |
| `16-oidc-keycloak-serverless.yaml` | Serverless | No | `https://<NGROK_URL>/realms/bootcamp` |
| `16-oidc-keycloak-hybrid.yaml` | Hybrid (Docker) | No | `http://host.docker.internal:8080/realms/bootcamp` |
| `16-oidc-introspection-serverless.yaml` | Serverless | Yes | `https://<NGROK_URL>/realms/bootcamp` |
| `16-oidc-introspection-hybrid.yaml` | Hybrid (Docker) | Yes | `http://host.docker.internal:8080/realms/bootcamp` |

**Test real-time revocation:**

```bash
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"   # → 200

# Log alice's sessions out via Keycloak's admin REST API
ADMIN=$(curl -s -H 'ngrok-skip-browser-warning: true' \
  -d 'grant_type=password' -d 'client_id=admin-cli' \
  -d 'username=admin' -d 'password=admin' \
  "$KC/realms/master/protocol/openid-connect/token" | jq -r .access_token)
ALICE_ID=$(curl -s -H "Authorization: Bearer $ADMIN" \
  "$KC/admin/realms/bootcamp/users?username=alice" | jq -r '.[0].id')
curl -s -X POST -H "Authorization: Bearer $ADMIN" \
  "$KC/admin/realms/bootcamp/users/$ALICE_ID/logout"

curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"   # → 401
```

With the **default** (offline JWKS) config, the last call would still return
`200` until the token expired - that's the difference introspection makes.

> **Clean up:** `deck gateway sync deck/01-services-and-routes.yaml …` removes
> the plugin; `cd ../keycloak && docker compose down -v` stops Keycloak.

---

### 17 - Upstream OAuth (Kong as the OAuth client)

Steps 15 and 16 made Kong **validate** tokens coming *from* callers.
[Upstream OAuth](https://developer.konghq.com/plugins/upstream-oauth/) is the
**mirror image**: Kong itself fetches a `client_credentials` token from the IdP
and injects it as `Authorization: Bearer …` on the **upstream** request - so your
backend gets a valid machine-to-machine token without the caller knowing anything
about OAuth. Classic use: a public/edge API whose upstream is a protected
internal service.

Scoped to `httpbun-service`, whose `/headers` echoes what the upstream received.
Uses the shared Keycloak's `kong-m2m` client.

> **No `iss` matching here.** Kong is the *client*, not the validator - it just
> forwards the token upstream. You only need the `token_endpoint` reachable from
> the DP. On serverless that's the **public ngrok URL** (the cloud DP can't reach
> `host.docker.internal`).

Edit `deck/17-upstream-oauth.yaml` and set `oauth.token_endpoint` to your ngrok
URL (`https://9805-49-249-135-74.ngrok-free.app/realms/bootcamp/protocol/openid-connect/token`),
then:

```bash
deck gateway apply deck/17-upstream-oauth.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name "$CP_NAME"
```

**Test - the caller sends nothing, the upstream sees a token:**

```bash
# Client sends NO Authorization header
curl -s $PROXY_URL/httpbun/headers | jq '.headers.Authorization'
# → "Bearer eyJhbGciOi..."  (Kong obtained this from Keycloak using kong-m2m)

# Decode it to prove it's a real M2M token minted for kong-m2m
curl -s $PROXY_URL/httpbun/headers | jq -r '.headers.Authorization' \
  | cut -d' ' -f2 | cut -d. -f2 | base64 -d 2>/dev/null | jq '{iss, azp, typ}'
# → { "iss": "https://9805-49-249-135-74.ngrok-free.app/realms/bootcamp", "azp": "kong-m2m", "typ": "Bearer" }
```

Kong caches the token (`cache.default_ttl`) so it isn't calling Keycloak on every
request; it auto-refreshes near expiry.

> **Clean up:** `deck gateway sync deck/01-services-and-routes.yaml …`.

---

## Insomnia Collection

Import `insomnia/kong-gateway-bootcamp.json` into Insomnia.

Switch to **"Konnect Serverless DP"** environment → sets `base_url` to your serverless proxy URL.

For JWT tests: generate a token, then set `jwt_token` in the Insomnia environment.

The collection also has folders **15 – Kong Identity**, **16 – Keycloak OIDC**,
and **17 – Upstream OAuth**. Their "POST get token" requests auto-store the token
in an environment variable (`keycloak_token` / `kong_identity_token`). On
serverless, point `keycloak_issuer` (and the upstream-oauth token endpoint) at
your public ngrok URL, and fill the `kong_identity_*` placeholders from your
Konnect Kong Identity auth server.

---

## Full Reset

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force
```

---

## Useful httpbun Paths

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
