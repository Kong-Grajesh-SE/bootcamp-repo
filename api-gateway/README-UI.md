# Kong API Gateway Bootcamp — Konnect UI Walkthrough

> 14-step hands-on lab using the Konnect web console. Each step adds one
> plugin (or one entity set) to a base of three upstream services so you
> can see exactly what each policy does without leaving the browser.

> **What you bring forward from the previous module:** the decK-driven
> `README-hybrid.md` (and `README-serverless.md`) walks you through the
> same fourteen demos as YAML you `deck gateway apply`. This guide
> rebuilds the *same configuration* in the Konnect UI — Services, Routes,
> Plugins, Consumers, Consumer Groups — so you can see where every decK
> field lives in the web console. The plugin names, scopes, and config
> values are intentionally identical, so feel free to switch back and
> forth between the YAML and the UI as you go.

---

## Prerequisites

1. **Konnect account** at [cloud.konghq.com](https://cloud.konghq.com)
2. **Control Plane** with a connected Data Plane (hybrid Docker DP or serverless)
3. **Proxy URL** — typically `http://localhost:8000` for a Docker DP, or the
   serverless proxy URL shown in **Gateway Manager → Control Plane → Overview**
4. **Insomnia** (optional) for replaying the test requests as a collection

```bash
export PROXY_URL=http://localhost:8000
```

> Replace `<your-control-plane>` everywhere below with the name of the
> control plane you're working in. Never hardcode a real CP name into
> shared notes — Konnect organisations and naming conventions vary.

---

## Backends used by every step

| Service | Backend | Protocol | Port |
|---------|---------|----------|------|
| `httpbin-service` | `httpbin.org` | HTTPS | 443 |
| `httpbun-service` | `httpbun.com` | HTTPS | 443 |
| `konghq-service` | `httpbin.konghq.com` | HTTP | 80 |

All three routes use `strip_path: on` so the prefix is dropped before the
upstream call. The same three services are reused across every step.

---

## Step 1 — Services & Routes

Build the base topology: three upstream services, each with one route.
After this step the proxy responds with real upstream payloads for
`/httpbin/*`, `/httpbun/*`, and `/konghq/*`.

### 1.1 Create the httpbin Service

1. Go to **Gateway Manager → `<your-control-plane>` → Gateway Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `httpbin-service`
   - **URL**: `https://httpbin.org`
   - **Retries**: `3`
   - **Connect Timeout**: `30000`
   - **Read Timeout**: `30000`
   - **Write Timeout**: `30000`
4. Click **Save**

### 1.2 Create the httpbin Route

1. On the `httpbin-service` detail page, open the **Routes** tab
2. Click **New Route**
3. Configure:
   - **Name**: `httpbin-route`
   - **Paths**: `/httpbin`
   - **Protocols**: `http`, `https`
   - **Strip Path**: `on`
4. Click **Save**

### 1.3 Create the httpbun Service

1. Back to **Gateway Services → New Gateway Service**
2. Configure:
   - **Name**: `httpbun-service`
   - **URL**: `https://httpbun.com`
   - **Retries**: `3`
   - **Connect/Read/Write Timeout**: `30000`
3. Click **Save**

### 1.4 Create the httpbun Route

1. On `httpbun-service` → **Routes** tab → **New Route**
2. Configure:
   - **Name**: `httpbun-route`
   - **Paths**: `/httpbun`
   - **Protocols**: `http`, `https`
   - **Strip Path**: `on`
3. Click **Save**

### 1.5 Create the konghq Service

1. **Gateway Services → New Gateway Service**
2. Configure:
   - **Name**: `konghq-service`
   - **URL**: `http://httpbin.konghq.com`
   - **Retries**: `3`
   - **Connect/Read/Write Timeout**: `30000`
3. Click **Save**

### 1.6 Create the konghq Route

1. On `konghq-service` → **Routes** tab → **New Route**
2. Configure:
   - **Name**: `konghq-route`
   - **Paths**: `/konghq`
   - **Protocols**: `http`, `https`
   - **Strip Path**: `on`
3. Click **Save**

### 1.7 Test — all three routes resolve

```bash
curl -s $PROXY_URL/httpbin/get | jq .origin
curl -s $PROXY_URL/httpbun/get | jq .url
curl -s $PROXY_URL/konghq/get | jq .origin
```

**Expected**: Three JSON bodies from three different upstreams. No `404`s.

### 1.8 Test — unknown path is rejected

```bash
curl -s $PROXY_URL/does-not-exist | jq .message
```

**Expected**: `"no Route matched with those values"`.

---

## Step 2 — Rate Limiting

Limit `httpbin-service` to **5 requests per minute per IP** so you can
see Kong's classic traffic-control plugin in action.

### 2.1 Add the Rate Limiting plugin

1. Navigate to **Gateway Services → `httpbin-service` → Plugins**
2. Click **New Plugin → Traffic Control → Rate Limiting**
3. Configure:
   - **Minute**: `5`
   - **Policy**: `local`
   - **Limit By**: `ip`
   - **Hide Client Headers**: `off`
   - **Fault Tolerant**: `on`
   - **Error Code**: `429`
   - **Error Message**: `Rate limit exceeded — try again later`
4. **Scope**: `Service` → `httpbin-service` (auto-selected)
5. Click **Save**

### 2.2 Test — first five requests succeed

```bash
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" $PROXY_URL/httpbin/get
done
```

**Expected**: Five `200`s. Response headers carry `X-RateLimit-Limit-Minute: 5`
and `X-RateLimit-Remaining-Minute` counting down.

### 2.3 Test — sixth request is throttled

```bash
curl -i $PROXY_URL/httpbin/get
```

**Expected**: `429 Too Many Requests` with the configured error message.

### 2.4 Test — httpbun is unaffected

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` — the plugin is scoped only to `httpbin-service`.

---

## Step 3 — Proxy Cache

Cache `GET`/`HEAD` responses from `httpbin-service` for **30 seconds** in
the data plane's in-memory store.

### 3.1 Add the Proxy Cache plugin

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Traffic Control → Proxy Cache**
2. Configure:
   - **Response Code**: `200`, `301`, `302`
   - **Request Method**: `GET`, `HEAD`
   - **Content Type**: `application/json`, `text/html`
   - **Cache TTL**: `30`
   - **Strategy**: `memory`
   - **Cache Control**: `off`
3. **Scope**: `Service` → `httpbin-service`
4. Click **Save**

### 3.2 Test — cache miss then hit

```bash
# First call — X-Cache-Status: Miss
curl -i $PROXY_URL/httpbin/get | grep -i x-cache-status

# Second call within 30s — X-Cache-Status: Hit
curl -i $PROXY_URL/httpbin/get | grep -i x-cache-status
```

**Expected**: First response shows `Miss`, second shows `Hit`.

### 3.3 Test — POST is bypassed

```bash
curl -i -X POST $PROXY_URL/httpbin/post -d '{}' | grep -i x-cache-status
```

**Expected**: `X-Cache-Status: Bypass` — `POST` is not in the cached methods.

---

## Step 4 — Upstream Load Balancing

Add a fourth service backed by a Kong **Upstream** (logical pool) so you
can see round-robin balancing across two real backends.

### 4.1 Create the Upstream

1. Go to **Gateway Manager → `<your-control-plane>` → Upstreams**
2. Click **New Upstream**
3. Configure:
   - **Name**: `demo-upstream`
   - **Algorithm**: `round-robin`
   - **Hash On**: `none`
4. Expand **Healthchecks → Active**:
   - **HTTP Path**: `/get`
   - **Type**: `https`
   - **Healthy Interval**: `10`
   - **Healthy Successes**: `3`
   - **Unhealthy Interval**: `10`
   - **Unhealthy HTTP Failures**: `3`
5. Expand **Healthchecks → Passive**:
   - **Healthy Successes**: `5`
   - **Unhealthy HTTP Failures**: `5`
6. Click **Save**

### 4.2 Add targets to the Upstream

1. On the `demo-upstream` detail page, open **Targets**
2. Click **New Target**, configure:
   - **Target**: `httpbin.org:443`
   - **Weight**: `50`
3. Click **Save**. Then **New Target** again:
   - **Target**: `httpbun.com:443`
   - **Weight**: `50`
4. Click **Save**

### 4.3 Create the load-balanced Service

1. **Gateway Services → New Gateway Service**
2. Configure:
   - **Name**: `loadbalanced-service`
   - **Host**: `demo-upstream`
   - **Port**: `443`
   - **Protocol**: `https`
   - **Path**: `/anything`
3. Click **Save**

### 4.4 Create the load-balanced Route

1. On `loadbalanced-service` → **Routes** → **New Route**
2. Configure:
   - **Name**: `loadbalanced-route`
   - **Paths**: `/lb`
   - **Protocols**: `http`, `https`
   - **Strip Path**: `on`
3. Click **Save**

### 4.5 Test — round-robin across upstreams

```bash
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
```

**Expected**: Output alternates between `httpbin.org/anything` and
`httpbun.com/anything` URLs.

---

## Step 5 — Key Auth (+ first consumers)

Lock `httpbin-service` behind an API key, then create two consumers so
the key check actually identifies *who* is calling.

> **Consumer — quick primer (covered in depth in Step 7):** A **consumer**
> in Kong is an identity that Kong knows about — typically a person, a
> service account, or a partner. Credentials (API key, JWT secret, OAuth
> client) are attached to a consumer, so when Kong validates a credential
> it can tell you *who* called the route. The two consumers below are
> created alongside the plugin so the demo is self-contained; Step 7
> unpacks the standalone consumer concept and Step 14 ties it together
> with consumer groups and ACL.

### 5.1 Add the Key Auth plugin

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Authentication → Key Authentication**
2. Configure:
   - **Key Names**: `apikey`
   - **Key In Header**: `on`
   - **Key In Query**: `on`
   - **Key In Body**: `off`
   - **Hide Credentials**: `on`
   - **Run On Preflight**: `on`
3. **Scope**: `Service` → `httpbin-service`
4. Click **Save**

### 5.2 Create consumer `demo-user`

1. Go to **Gateway Manager → `<your-control-plane>` → Consumers**
2. Click **New Consumer**
3. Configure:
   - **Username**: `demo-user`
   - **Custom ID**: `demo-001`
4. Click **Save**
5. Open the consumer → **Credentials** tab → **New Key Auth Credential**
   - **Key**: `my-secret-key-123`
6. Click **Save**

### 5.3 Create consumer `test-user`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `test-user`
   - **Custom ID**: `test-002`
3. Click **Save**
4. **Credentials** tab → **New Key Auth Credential**
   - **Key**: `test-key-456`
5. Click **Save**

### 5.4 Test — no key is rejected

```bash
curl -i $PROXY_URL/httpbin/get
```

**Expected**: `401 Unauthorized`.

### 5.5 Test — key in header

```bash
curl -i $PROXY_URL/httpbin/get -H "apikey: my-secret-key-123"
```

**Expected**: `200`. Upstream sees `X-Consumer-Username: demo-user`.

### 5.6 Test — key in query string

```bash
curl -i "$PROXY_URL/httpbin/get?apikey=my-secret-key-123"
```

**Expected**: `200` — both header and query are accepted.

### 5.7 Test — wrong key

```bash
curl -i $PROXY_URL/httpbin/get -H "apikey: wrong-key"
```

**Expected**: `401`.

### 5.8 Test — httpbun is still open

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` — `key-auth` is scoped to `httpbin-service` only.

---

## Step 6 — JWT Auth

Protect `httpbun-service` with JWT bearer tokens signed by a shared
HS256 secret. The plugin verifies `exp` and reads the issuer from `iss`.

> **Secret rotation:** generate a real HS256 secret before creating the
> credential below. Never use the literal placeholder string:
> ```bash
> JWT_SECRET=$(openssl rand -hex 32)
> echo $JWT_SECRET
> ```

### 6.1 Add the JWT plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Authentication → JWT**
2. Configure:
   - **Claims To Verify**: `exp`
   - **Header Names**: `Authorization`
   - **Key Claim Name**: `iss`
   - **Secret Is Base64**: `off`
   - **Run On Preflight**: `on`
   - **URI Param Names**: `jwt`
3. **Scope**: `Service` → `httpbun-service`
4. Click **Save**

### 6.2 Create consumer `jwt-user` with a JWT credential

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `jwt-user`
   - **Custom ID**: `jwt-001`
3. Click **Save**
4. Open the consumer → **Credentials** tab → **New JWT Credential**
   - **Algorithm**: `HS256`
   - **Key**: `my-jwt-issuer` (this is the value the plugin will match against the `iss` claim)
   - **Secret**: `<REPLACE-WITH-RANDOM-SECRET>` — paste the value of `$JWT_SECRET`
     you generated above (`openssl rand -hex 32`). Never reuse the literal placeholder.
5. Click **Save**

### 6.3 Mint a JWT signed with that secret

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

### 6.4 Test — no token is rejected

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `401 Unauthorized`.

### 6.5 Test — valid JWT is accepted

```bash
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"
```

**Expected**: `200`. Upstream sees `X-Consumer-Username: jwt-user`.

### 6.6 Test — expired/invalid token

```bash
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer not-a-real-jwt"
```

**Expected**: `401` — JWT parser rejects the malformed token.

---

## Step 7 — Consumers

Now that you've seen consumers attached to a plugin, create three
**standalone** consumers that reuse the existing `key-auth` plugin on
`httpbin-service`. This is the everyday "add a new client" workflow.

> **Prerequisite:** Step 5 must already be in place — the `key-auth`
> plugin on `httpbin-service` is what gives these new keys meaning.

### 7.1 Create consumer `alice`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `alice`
   - **Custom ID**: `alice-001`
3. Click **Save**
4. **Credentials → New Key Auth Credential**
   - **Key**: `alice-api-key`
5. Click **Save**

### 7.2 Create consumer `bob`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `bob`
   - **Custom ID**: `bob-002`
3. Click **Save**
4. **Credentials → New Key Auth Credential**
   - **Key**: `bob-api-key`
5. Click **Save**

### 7.3 Create consumer `charlie`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `charlie`
   - **Custom ID**: `charlie-003`
3. Click **Save**
4. **Credentials → New Key Auth Credential**
   - **Key**: `charlie-api-key`
5. Click **Save**

### 7.4 Test — each key identifies its consumer

```bash
curl -s $PROXY_URL/httpbin/get -H "apikey: alice-api-key"   | jq '.headers["X-Consumer-Username"]'
curl -s $PROXY_URL/httpbin/get -H "apikey: bob-api-key"     | jq '.headers["X-Consumer-Username"]'
curl -s $PROXY_URL/httpbin/get -H "apikey: charlie-api-key" | jq '.headers["X-Consumer-Username"]'
```

**Expected**: `"alice"`, `"bob"`, `"charlie"` — Kong injects the
consumer username on every authenticated request.

### 7.5 Test — unknown key still rejected

```bash
curl -i $PROXY_URL/httpbin/get -H "apikey: nobody-knows"
```

**Expected**: `401`.

---

## Step 8 — CORS (global)

Allow browser-based clients on three specific origins to call any route
in the control plane. CORS is applied **globally** (no service/route scope).

### 8.1 Add the CORS plugin

1. Go to **Gateway Manager → `<your-control-plane>` → Plugins**
2. Click **New Plugin → Security → CORS**
3. Configure:
   - **Origins**: `http://localhost:3000`, `http://localhost:5173`, `https://example.com`
   - **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
   - **Headers**: `Content-Type`, `Authorization`, `apikey`, `X-Custom-Header`, `X-Correlation-ID`
   - **Credentials**: `on`
   - **Max Age**: `3600`
   - **Preflight Continue**: `off`
4. **Scope**: `Global` (leave service/route blank)
5. Click **Save**

### 8.2 Test — simple cross-origin request

```bash
curl -i $PROXY_URL/httpbin/get -H "Origin: http://localhost:3000"
```

**Expected**: `200` with `Access-Control-Allow-Origin: http://localhost:3000`.

### 8.3 Test — preflight (OPTIONS)

```bash
curl -i -X OPTIONS $PROXY_URL/httpbin/get \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

**Expected**: `204` with `Access-Control-Allow-Methods` listing all six methods.

### 8.4 Test — disallowed origin

```bash
curl -i $PROXY_URL/httpbin/get -H "Origin: https://evil.example.org"
```

**Expected**: `200` but no `Access-Control-Allow-Origin` header — the browser
will block this client-side.

---

## Step 9 — IP Restriction

Restrict `httpbin-service` so only RFC 1918 private ranges and loopback
can reach it. Important: when the data plane runs in Docker, your client
IP arrives as a Docker bridge address in `172.16.0.0/12`.

### 9.1 Add the IP Restriction plugin

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Security → IP Restriction**
2. Configure **Allow** (one per row):
   - `127.0.0.0/8`
   - `10.0.0.0/8`
   - `172.16.0.0/12`
   - `192.168.0.0/16`
   - `::1`
3. Configure:
   - **Message**: `Your IP address is not allowed`
4. **Scope**: `Service` → `httpbin-service`
5. Click **Save**

### 9.2 Test — allowed source

```bash
curl -i $PROXY_URL/httpbin/get
```

**Expected**: `200` — Docker bridge IP (`172.x.x.x`) is in the allow list.

### 9.3 Test — disallowed source

Temporarily remove `172.16.0.0/12` from the allow list, save, then:

```bash
curl -i $PROXY_URL/httpbin/get
```

**Expected**: `403 Forbidden` with the configured message. Re-add the
CIDR when you're done to keep the rest of the lab working.

---

## Step 10 — Correlation ID (global)

Inject a unique `X-Correlation-ID` header on every request so you can
trace a call end-to-end through your logs.

### 10.1 Add the Correlation ID plugin

1. Go to **Gateway Manager → `<your-control-plane>` → Plugins**
2. Click **New Plugin → Tracing → Correlation ID**
3. Configure:
   - **Header Name**: `X-Correlation-ID`
   - **Generator**: `uuid#counter`
   - **Echo Downstream**: `on`
4. **Scope**: `Global`
5. Click **Save**

### 10.2 Test — header is generated

```bash
curl -i $PROXY_URL/httpbin/get | grep -i x-correlation-id
```

**Expected**: `X-Correlation-ID: <uuid>#1` (the counter increments per request).

### 10.3 Test — upstream sees the same ID

```bash
curl -s $PROXY_URL/httpbin/headers | jq '.headers["X-Correlation-Id"]'
```

**Expected**: Same UUID was forwarded to `httpbin.org`.

### 10.4 Test — client-supplied ID is preserved

```bash
curl -i $PROXY_URL/httpbin/get -H "X-Correlation-ID: my-trace-123"
```

**Expected**: Response echoes `X-Correlation-ID: my-trace-123`.

---

## Step 11 — Request Transformer

Add headers and query params to requests as they leave Kong toward
`httpbin-service`, and rename one incoming header.

### 11.1 Add the Request Transformer plugin

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Transformations → Request Transformer**
2. Configure **Add**:
   - **Headers**:
     - `X-Added-By:Kong-Gateway`
     - `X-Bootcamp:API-Gateway-Demo`
   - **Querystring**:
     - `source:kong`
     - `gateway:true`
3. Configure **Rename**:
   - **Headers**: `Accept:X-Original-Accept`
4. Leave **Replace**, **Remove**, **Append** empty
5. **Scope**: `Service` → `httpbin-service`
6. Click **Save**

### 11.2 Test — added headers reach the upstream

```bash
curl -s $PROXY_URL/httpbin/headers | jq '.headers'
```

**Expected**: Output includes `"X-Added-By": "Kong-Gateway"` and
`"X-Bootcamp": "API-Gateway-Demo"`.

### 11.3 Test — added query params reach the upstream

```bash
curl -s $PROXY_URL/httpbin/get | jq '.args'
```

**Expected**: `{ "source": "kong", "gateway": "true" }`.

### 11.4 Test — header rename

```bash
curl -s $PROXY_URL/httpbin/headers -H "Accept: application/json" \
  | jq '.headers | {accept: ."Accept", original: ."X-Original-Accept"}'
```

**Expected**: `Accept` is gone (or empty), `X-Original-Accept` carries
`application/json`.

---

## Step 12 — Response Transformer

Reshape the response on the way back: add three headers, strip two
upstream-leaked headers (`Server`, `Via`).

### 12.1 Add the Response Transformer plugin

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Transformations → Response Transformer**
2. Configure **Add**:
   - **Headers**:
     - `X-Powered-By:Kong-Gateway`
     - `X-Bootcamp-Demo:true`
     - `X-Environment:bootcamp`
3. Configure **Remove**:
   - **Headers**: `Server`, `Via`
4. Leave **Replace**, **Rename**, **Append** empty
5. **Scope**: `Service` → `httpbin-service`
6. Click **Save**

### 12.2 Test — headers added and removed

```bash
curl -i $PROXY_URL/httpbin/get | grep -iE "^(server|via|x-powered-by|x-bootcamp-demo|x-environment):"
```

**Expected**:
- `X-Powered-By: Kong-Gateway`
- `X-Bootcamp-Demo: true`
- `X-Environment: bootcamp`
- *No* `Server:` or `Via:` headers.

---

## Step 13 — HTTP Log

Stream a JSON log entry to an external endpoint after every proxied
request. The bootcamp uses [webhook.site](https://webhook.site) so you can see
log lines arrive in your browser in real time.

> **Before applying:** open [webhook.site](https://webhook.site), copy your
> unique URL, and substitute it into the `HTTP Endpoint` field below.
> Never leave the literal `<YOUR-UNIQUE-ID>` placeholder in a real config.

### 13.1 Add the HTTP Log plugin

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Logging → HTTP Log**
2. Configure:
   - **HTTP Endpoint**: `https://webhook.site/<YOUR-UNIQUE-ID>`
     (paste your real webhook.site URL — do **not** leave the placeholder)
   - **Method**: `POST`
   - **Content Type**: `application/json`
   - **Timeout**: `10000`
   - **Keepalive**: `60000`
   - **Flush Timeout**: `2`
   - **Retry Count**: `3`
3. **Scope**: `Service` → `httpbin-service`
4. Click **Save**

### 13.2 Test — logs appear at webhook.site

```bash
curl -s $PROXY_URL/httpbin/get > /dev/null
curl -s $PROXY_URL/httpbin/get > /dev/null
curl -s $PROXY_URL/httpbin/get > /dev/null
```

**Expected**: Three JSON entries land in your webhook.site inbox within
a few seconds, each containing the full Kong log object (request,
response, latencies, route, service, consumer).

> **Local alternative:** if you'd rather log to a local listener, change
> **HTTP Endpoint** to `http://host.docker.internal:9999/log` and run a
> minimal receiver, e.g. `python3 -m http.server 9999`.

---

## Step 14 — Consumer Groups + ACL

The capstone demo: combine three Kong features to build a tiered API
access system on `httpbin-service`.

1. **Key Auth** — identifies *who* is calling (authentication)
2. **ACL (Access Control List)** — decides *if* they're allowed (authorization)
3. **Consumer Groups** — applies *different rate limits per tier* (policy)

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

> **Key concept:** ACL group ≠ Consumer Group.
> - **ACL group** (e.g., `premium`) → used by the ACL plugin for authorization
> - **Consumer Group** (e.g., `premium-tier`) → used for group-scoped rate limiting
> - A consumer can belong to both, independently

> **Reset first:** if Step 5 / Step 7 already added a `key-auth` plugin
> and other consumers to `httpbin-service`, delete them before starting
> this step so the only auth path is the one you build below.

### 14.1 Add Key Auth to httpbin-service

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Authentication → Key Authentication**
2. Configure:
   - **Key Names**: `apikey`
   - **Hide Credentials**: `on`
3. **Scope**: `Service` → `httpbin-service`
4. Click **Save**

### 14.2 Add ACL to httpbin-service

1. **Gateway Services → `httpbin-service` → Plugins → New Plugin → Security → ACL**
2. Configure:
   - **Allow**: `premium`, `standard`
   - **Hide Groups Header**: `off`
3. **Scope**: `Service` → `httpbin-service`
4. Click **Save**

### 14.3 Create consumer `premium-user`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `premium-user`
   - **Custom ID**: `premium-001`
3. Click **Save**
4. **Credentials → New Key Auth Credential**
   - **Key**: `premium-key-123`
5. Click **Save**
6. **ACLs** tab → **Add Group**
   - **Group**: `premium`
7. Click **Save**

### 14.4 Create consumer `standard-user`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `standard-user`
   - **Custom ID**: `standard-002`
3. Click **Save**
4. **Credentials → New Key Auth Credential**
   - **Key**: `standard-key-456`
5. Click **Save**
6. **ACLs** tab → **Add Group**
   - **Group**: `standard`
7. Click **Save**

### 14.5 Create consumer `trial-user`

1. **Consumers → New Consumer**
2. Configure:
   - **Username**: `trial-user`
   - **Custom ID**: `trial-003`
3. Click **Save**
4. **Credentials → New Key Auth Credential**
   - **Key**: `blocked-key-789`
5. Click **Save**
6. **ACLs** tab → **Add Group**
   - **Group**: `trial` *(NOT in the ACL allow list — this consumer will get `403`)*
7. Click **Save**

### 14.6 Create consumer group `premium-tier`

1. Go to **Gateway Manager → `<your-control-plane>` → Consumer Groups**
2. Click **New Consumer Group**
3. Configure:
   - **Name**: `premium-tier`
4. Click **Save**
5. **Members** tab → **Add Consumer** → select `premium-user`
6. **Plugins** tab → **New Plugin → Traffic Control → Rate Limiting**
   - **Minute**: `1000`
   - **Policy**: `local`
7. Click **Save**

### 14.7 Create consumer group `standard-tier`

1. **Consumer Groups → New Consumer Group**
2. Configure:
   - **Name**: `standard-tier`
3. Click **Save**
4. **Members** tab → **Add Consumer** → select `standard-user`
5. **Plugins** tab → **New Plugin → Traffic Control → Rate Limiting**
   - **Minute**: `10`
   - **Policy**: `local`
6. Click **Save**

### 14.8 Verify the full setup

In **Gateway Services → `httpbin-service` → Plugins** you should see
`key-auth` and `acl` (the rate-limiting plugins live on the consumer
groups, not the service).

In **Consumers** you should see `premium-user`, `standard-user`,
`trial-user`. Open each one and confirm:

- `premium-user` → Credentials: `premium-key-123` · ACLs: `premium` · Groups: `premium-tier`
- `standard-user` → Credentials: `standard-key-456` · ACLs: `standard` · Groups: `standard-tier`
- `trial-user` → Credentials: `blocked-key-789` · ACLs: `trial` · Groups: *(none)*

In **Consumer Groups**:
- `premium-tier` — 1 member · rate-limiting `1000/min`
- `standard-tier` — 1 member · rate-limiting `10/min`

### 14.9 Test — no key

```bash
curl -i $PROXY_URL/httpbin/get
```

**Expected**: `401 Unauthorized`.

### 14.10 Test — premium tier (high limit)

```bash
curl -i $PROXY_URL/httpbin/get -H "apikey: premium-key-123"
```

**Expected**: `200` with headers:
- `X-RateLimit-Limit-Minute: 1000`
- `X-Consumer-Username: premium-user`
- `X-Consumer-Groups: premium-tier`

### 14.11 Test — standard tier (low limit)

```bash
curl -i $PROXY_URL/httpbin/get -H "apikey: standard-key-456"
```

**Expected**: `200` with:
- `X-RateLimit-Limit-Minute: 10`
- `X-Consumer-Username: standard-user`
- `X-Consumer-Groups: standard-tier`

### 14.12 Test — trial tier (authenticated but blocked)

```bash
curl -i $PROXY_URL/httpbin/get -H "apikey: blocked-key-789"
```

**Expected**: `403` with body `{"message":"You cannot consume this service"}` —
key-auth passes (the key is valid), but ACL blocks the `trial` group.

### 14.13 Test — standard tier exceeds its limit

```bash
for i in $(seq 1 12); do
  code=$(curl -s -o /dev/null -w "%{http_code}" $PROXY_URL/httpbin/get \
    -H "apikey: standard-key-456")
  echo "Request $i: HTTP $code"
done
```

**Expected**: First 10 → `200`, then `429` as the consumer-group rate
limit kicks in. (Reset the counter by waiting 60 seconds.)

### 14.14 Test — httpbun still open

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` — all the Step 14 plugins are scoped to `httpbin-service`.

#### Real-world mapping

This pattern maps directly to SaaS API tiers:

| Tier | What they get | Maps to |
|------|---------------|---------|
| **Free** | Authenticated but blocked from premium endpoints | `trial-user` (ACL denied) |
| **Standard** | Access with modest rate limits | `standard-user` (10 req/min) |
| **Enterprise** | Access with high rate limits | `premium-user` (1000 req/min) |

In production you'd combine this with Dev Portal **App Registration** so
consumers and credentials are auto-provisioned when users subscribe to a plan.

---

## Cleanup

To reset back to the base topology of Step 1 (three services + three routes):

1. **Gateway Manager → `<your-control-plane>` → Plugins** — delete each plugin
   you added (`rate-limiting`, `proxy-cache`, `key-auth`, `jwt`, `cors`,
   `ip-restriction`, `correlation-id`, `request-transformer`,
   `response-transformer`, `http-log`, `acl`)
2. **Consumers** — delete `demo-user`, `test-user`, `jwt-user`, `alice`,
   `bob`, `charlie`, `premium-user`, `standard-user`, `trial-user`
3. **Consumer Groups** — delete `premium-tier`, `standard-tier`
4. **Upstreams** — delete `demo-upstream`
5. **Gateway Services** — delete `loadbalanced-service` (cascades to its route)
6. Leave `httpbin-service`, `httpbun-service`, `konghq-service` in place if
   you want to keep the base topology; otherwise delete those too.

To wipe the control plane entirely (services, routes, plugins, consumers,
consumer groups, upstreams) from the CLI:

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "<your-control-plane>" \
  --force
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401` after adding consumers | Confirm the credential is attached to the right consumer and the `apikey` header value matches exactly |
| `403 Your IP address is not allowed` | Add `172.16.0.0/12` to IP Restriction allow list — Docker DPs see the client as a bridge IP |
| `429` immediately on first request | Step 2 (per-IP) and Step 14 (per-consumer-group) limits stack — disable one when testing the other |
| `X-Cache-Status: Bypass` on a `GET` | Method/content-type must be in the Proxy Cache config — check `request_method` and `content_type` |
| `403 You cannot consume this service` with a valid key | ACL plugin allow list doesn't include the consumer's ACL group — re-check Step 14.2 |
| HTTP Log shows nothing at webhook.site | The endpoint URL still has `<YOUR-UNIQUE-ID>` — paste your real webhook.site URL into the plugin |
| Round-robin not alternating | Send 4+ requests; check `.url` field to confirm the upstream actually changes |
| Plugin not visible in UI | Confirm Kong Gateway data plane is 3.7+; some plugin names differ slightly across versions |
| `no Route matched` after a UI save | Wait ~5 seconds for config to propagate to the data plane, then retry |
