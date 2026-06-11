# Kong API Gateway Bootcamp - Konnect UI Walkthrough

> 17-step hands-on lab using the Konnect web console. Each step adds one
> plugin (or one entity set) to a base of three upstream services so you
> can see exactly what each policy does without leaving the browser.
> Steps 15–17 introduce Konnect-native (Kong Identity) and external-IdP
> (Auth0) OAuth2 / OpenID Connect, plus Upstream OAuth (Kong as the
> OAuth client to the backend).

> **What you bring forward from the previous module:** the decK-driven
> `README.md` walks you through the same demos as YAML you
> `deck gateway apply`. This guide
> rebuilds the *same configuration* in the Konnect UI - Services, Routes,
> Plugins, Consumers, Consumer Groups - so you can see where every decK
> field lives in the web console. The plugin names, scopes, and config
> values are intentionally identical, so feel free to switch back and
> forth between the YAML and the UI as you go.

---

## Prerequisites

1. **Konnect account** at [cloud.konghq.com](https://cloud.konghq.com)
2. **Control Plane** with a **Konnect Serverless Data Plane** provisioned
3. **Proxy URL** - the serverless proxy URL shown in **Gateway Manager → Control Plane → Overview**
4. **Auth0 tenant** (free tier is fine) for steps 16 and 17
5. **Insomnia** (optional) for replaying the test requests as a collection

```bash
export PROXY_URL=https://<YOUR_SERVERLESS_PROXY_URL>
```

> **Finding your serverless proxy URL:** In Konnect, go to **Gateway Manager →
> your-control-plane → Overview**. The proxy URL is shown under the serverless
> data plane section (e.g. `https://<id>.us.kong-dp.konghq.tech`).

> Replace `<your-control-plane>` everywhere below with the name of the
> control plane you're working in. Never hardcode a real CP name into
> shared notes - Konnect organisations and naming conventions vary.

---

## Backend used by every step

| Service | Backend | Protocol | Port |
|---------|---------|----------|------|
| `httpbun-service` | `httpbun.com` | HTTPS | 443 |

The route uses `strip_path: on` so the prefix is dropped before the
upstream call. The same service is reused across every step.

---

## Step 1 - Services & Routes

Build the base topology: one upstream service with one route.
After this step the proxy responds with real upstream payloads at
`/httpbun/*`.

### 1.1 Create the httpbun Service

1. Go to **Gateway Manager → `<your-control-plane>` → Gateway Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `httpbun-service`
   - **URL**: `https://httpbun.com`
   - **Retries**: `3`
   - **Connect Timeout**: `30000`
   - **Read Timeout**: `30000`
   - **Write Timeout**: `30000`
4. Click **Save**

### 1.2 Create the httpbun Route

1. On the `httpbun-service` detail page, open the **Routes** tab
2. Click **New Route**
3. Configure:
   - **Name**: `httpbun-route`
   - **Paths**: `/httpbun`
   - **Protocols**: `http`, `https`
   - **Strip Path**: `on`
4. Click **Save**

### 1.3 Test - route resolves

```bash
curl -s $PROXY_URL/httpbun/get | jq .url
```

**Expected**: JSON body from httpbun.com. No `404`.

### 1.4 Test - unknown path is rejected

```bash
curl -s $PROXY_URL/does-not-exist | jq .message
```

**Expected**: `"no Route matched with those values"`.

---

## Step 2 - Rate Limiting

Limit `httpbun-service` to **5 requests per minute per IP** so you can
see Kong's classic traffic-control plugin in action.

### 2.1 Add the Rate Limiting plugin

1. Navigate to **Gateway Services → `httpbun-service` → Plugins**
2. Click **New Plugin → Traffic Control → Rate Limiting**
3. Configure:
   - **Minute**: `5`
   - **Policy**: `local`
   - **Limit By**: `ip`
   - **Hide Client Headers**: `off`
   - **Fault Tolerant**: `on`
   - **Error Code**: `429`
   - **Error Message**: `Rate limit exceeded - try again later`
4. **Scope**: `Service` → `httpbun-service` (auto-selected)
5. Click **Save**

### 2.2 Test - first five requests succeed

```bash
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" $PROXY_URL/httpbun/get
done
```

**Expected**: Five `200`s. Response headers carry `X-RateLimit-Limit-Minute: 5`
and `X-RateLimit-Remaining-Minute` counting down.

### 2.3 Test - sixth request is throttled

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `429 Too Many Requests` with the configured error message.

### 2.4 Test - httpbun is unaffected

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` - the plugin is scoped only to `httpbun-service`.

---

## Step 3 - Proxy Cache

Cache `GET`/`HEAD` responses from `httpbun-service` for **30 seconds** in
the data plane's in-memory store.

### 3.1 Add the Proxy Cache plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Traffic Control → Proxy Cache**
2. Configure:
   - **Response Code**: `200`, `301`, `302`
   - **Request Method**: `GET`, `HEAD`
   - **Content Type**: `application/json`, `text/html`
   - **Cache TTL**: `30`
   - **Strategy**: `memory`
   - **Cache Control**: `off`
3. **Scope**: `Service` → `httpbun-service`
4. Click **Save**

### 3.2 Test - cache miss then hit

```bash
# First call - X-Cache-Status: Miss
curl -i $PROXY_URL/httpbun/get | grep -i x-cache-status

# Second call within 30s - X-Cache-Status: Hit
curl -i $PROXY_URL/httpbun/get | grep -i x-cache-status
```

**Expected**: First response shows `Miss`, second shows `Hit`.

### 3.3 Test - POST is bypassed

```bash
curl -i -X POST $PROXY_URL/httpbun/post -d '{}' | grep -i x-cache-status
```

**Expected**: `X-Cache-Status: Bypass` - `POST` is not in the cached methods.

---

## Step 4 - Upstream Load Balancing

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

### 4.5 Test - round-robin across upstreams

```bash
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
curl -s $PROXY_URL/lb | jq .url
```

**Expected**: Output alternates between `httpbin.org/anything` and
`httpbun.com/anything` URLs.

---

## Step 5 - Key Auth (+ first consumers)

Lock `httpbun-service` behind an API key, then create two consumers so
the key check actually identifies *who* is calling.

> **Consumer - quick primer (covered in depth in Step 7):** A **consumer**
> in Kong is an identity that Kong knows about - typically a person, a
> service account, or a partner. Credentials (API key, JWT secret, OAuth
> client) are attached to a consumer, so when Kong validates a credential
> it can tell you *who* called the route. The two consumers below are
> created alongside the plugin so the demo is self-contained; Step 7
> unpacks the standalone consumer concept and Step 14 ties it together
> with consumer groups and ACL.

### 5.1 Add the Key Auth plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Authentication → Key Authentication**
2. Configure:
   - **Key Names**: `apikey`
   - **Key In Header**: `on`
   - **Key In Query**: `on`
   - **Key In Body**: `off`
   - **Hide Credentials**: `on`
   - **Run On Preflight**: `on`
3. **Scope**: `Service` → `httpbun-service`
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

### 5.4 Test - no key is rejected

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `401 Unauthorized`.

### 5.5 Test - key in header

```bash
curl -i $PROXY_URL/httpbun/get -H "apikey: my-secret-key-123"
```

**Expected**: `200`. Upstream sees `X-Consumer-Username: demo-user`.

### 5.6 Test - key in query string

```bash
curl -i "$PROXY_URL/httpbun/get?apikey=my-secret-key-123"
```

**Expected**: `200` - both header and query are accepted.

### 5.7 Test - wrong key

```bash
curl -i $PROXY_URL/httpbun/get -H "apikey: wrong-key"
```

**Expected**: `401`.

### 5.8 Test - httpbun is still open

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` - `key-auth` is scoped to `httpbun-service` only.

---

## Step 6 - JWT Auth

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
   - **Secret**: `<REPLACE-WITH-RANDOM-SECRET>` - paste the value of `$JWT_SECRET`
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

### 6.4 Test - no token is rejected

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `401 Unauthorized`.

### 6.5 Test - valid JWT is accepted

```bash
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"
```

**Expected**: `200`. Upstream sees `X-Consumer-Username: jwt-user`.

### 6.6 Test - expired/invalid token

```bash
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer not-a-real-jwt"
```

**Expected**: `401` - JWT parser rejects the malformed token.

---

## Step 7 - Consumers

Now that you've seen consumers attached to a plugin, create three
**standalone** consumers that reuse the existing `key-auth` plugin on
`httpbun-service`. This is the everyday "add a new client" workflow.

> **Prerequisite:** Step 5 must already be in place - the `key-auth`
> plugin on `httpbun-service` is what gives these new keys meaning.

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

### 7.4 Test - each key identifies its consumer

```bash
curl -s $PROXY_URL/httpbun/get -H "apikey: alice-api-key"   | jq '.headers["X-Consumer-Username"]'
curl -s $PROXY_URL/httpbun/get -H "apikey: bob-api-key"     | jq '.headers["X-Consumer-Username"]'
curl -s $PROXY_URL/httpbun/get -H "apikey: charlie-api-key" | jq '.headers["X-Consumer-Username"]'
```

**Expected**: `"alice"`, `"bob"`, `"charlie"` - Kong injects the
consumer username on every authenticated request.

### 7.5 Test - unknown key still rejected

```bash
curl -i $PROXY_URL/httpbun/get -H "apikey: nobody-knows"
```

**Expected**: `401`.

---

## Step 8 - CORS (global)

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

### 8.2 Test - simple cross-origin request

```bash
curl -i $PROXY_URL/httpbun/get -H "Origin: http://localhost:3000"
```

**Expected**: `200` with `Access-Control-Allow-Origin: http://localhost:3000`.

### 8.3 Test - preflight (OPTIONS)

```bash
curl -i -X OPTIONS $PROXY_URL/httpbun/get \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

**Expected**: `204` with `Access-Control-Allow-Methods` listing all six methods.

### 8.4 Test - disallowed origin

```bash
curl -i $PROXY_URL/httpbun/get -H "Origin: https://evil.example.org"
```

**Expected**: `200` but no `Access-Control-Allow-Origin` header - the browser
will block this client-side.

---

## Step 9 - IP Restriction

Restrict `httpbun-service` so only specific IP ranges can reach it.
With a serverless data plane, your client IP is your actual public IP.

### 9.1 Add the IP Restriction plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Security → IP Restriction**
2. Configure **Allow** (one per row):
   - `127.0.0.0/8`
   - `10.0.0.0/8`
   - `172.16.0.0/12`
   - `192.168.0.0/16`
   - `::1`
3. Configure:
   - **Message**: `Your IP address is not allowed`
4. **Scope**: `Service` → `httpbun-service`
5. Click **Save**

### 9.2 Test - allowed source

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` - your public IP should be in one of the allow list CIDRs.
Check your IP with `curl -s httpbun.com/ip | jq .origin`.

### 9.3 Test - disallowed source

Temporarily remove `172.16.0.0/12` from the allow list, save, then:

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `403 Forbidden` with the configured message. Re-add the
CIDR when you're done to keep the rest of the lab working.

---

## Step 10 - Correlation ID (global)

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

### 10.2 Test - header is generated

```bash
curl -i $PROXY_URL/httpbun/get | grep -i x-correlation-id
```

**Expected**: `X-Correlation-ID: <uuid>#1` (the counter increments per request).

### 10.3 Test - upstream sees the same ID

```bash
curl -s $PROXY_URL/httpbun/headers | jq '.headers["X-Correlation-Id"]'
```

**Expected**: Same UUID was forwarded to `httpbun.com`.

### 10.4 Test - client-supplied ID is preserved

```bash
curl -i $PROXY_URL/httpbun/get -H "X-Correlation-ID: my-trace-123"
```

**Expected**: Response echoes `X-Correlation-ID: my-trace-123`.

---

## Step 11 - Request Transformer

Demonstrate all five transformer operations on requests as they leave Kong
toward `httpbun-service`: **add**, **rename**, **replace**, **remove**, and
**append**.

### 11.1 Add the Request Transformer plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Transformations → Request Transformer**
2. Configure **Add**:
   - **Headers**:
     - `X-Added-By:Kong-Gateway`
     - `X-Bootcamp:API-Gateway-Demo`
   - **Querystring**:
     - `source:kong`
     - `gateway:true`
3. Configure **Rename**:
   - **Headers**: `Accept:X-Original-Accept`
4. Configure **Replace**:
   - **Headers**: `X-Env:production`
5. Configure **Remove**:
   - **Headers**: `X-Remove-Me`
   - **Querystring**: `internal_debug`
6. Configure **Append**:
   - **Headers**: `X-Tags:kong-appended`
7. **Scope**: `Service` → `httpbun-service`
8. Click **Save**

### 11.2 Test - added headers reach the upstream

```bash
curl -s $PROXY_URL/httpbun/headers | jq '.headers'
```

**Expected**: Output includes `"X-Added-By": "Kong-Gateway"` and
`"X-Bootcamp": "API-Gateway-Demo"`.

### 11.3 Test - added query params reach the upstream

```bash
curl -s $PROXY_URL/httpbun/get | jq '.args'
```

**Expected**: `{ "source": "kong", "gateway": "true" }`.

### 11.4 Test - header rename

```bash
curl -s $PROXY_URL/httpbun/headers -H "Accept: application/json" \
  | jq '.headers | {accept: ."Accept", original: ."X-Original-Accept"}'
```

**Expected**: `Accept` is gone (or empty), `X-Original-Accept` carries
`application/json`.

### 11.5 Test - replace overwrites existing header value

```bash
curl -s $PROXY_URL/httpbun/headers -H "X-Env: staging" \
  | jq '.headers["X-Env"]'
```

**Expected**: `"production"` (Replace rewrites the value only when the
header is already present).

### 11.6 Test - remove strips header and query param

```bash
curl -s "$PROXY_URL/httpbun/headers?internal_debug=1" -H "X-Remove-Me: secret" \
  | jq '{headers: .headers["X-Remove-Me"], args: .args.internal_debug}'
```

**Expected**: Both values are `null` - the plugin stripped them before
the request reached the upstream.

### 11.7 Test - append adds to existing header

```bash
curl -s $PROXY_URL/httpbun/headers -H "X-Tags: first" \
  | jq '.headers["X-Tags"]'
```

**Expected**: `"first,kong-appended"` (Append adds the value; if the header
was absent, it creates it with just `kong-appended`).

---

## Step 12 - Response Transformer

Demonstrate all five transformer operations on responses: **add**, **rename**,
**replace**, **remove**, and **append**.

### 12.1 Add the Response Transformer plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Transformations → Response Transformer**
2. Configure **Add**:
   - **Headers**:
     - `X-Powered-By:Kong-Gateway`
     - `X-Bootcamp-Demo:true`
     - `X-Environment:bootcamp`
3. Configure **Rename**:
   - **Headers**: `Date:X-Response-Date`
4. Configure **Replace**:
   - **Headers**: `Content-Type:application/json; charset=utf-8`
5. Configure **Remove**:
   - **Headers**: `X-Powered-By`, `Alt-Svc`
6. Configure **Append**:
   - **Headers**: `X-Cache-Tags:kong-gateway`
7. **Scope**: `Service` → `httpbun-service`
8. Click **Save**

### 12.2 Test - headers added and removed

```bash
curl -i $PROXY_URL/httpbun/get | grep -iE "^(x-powered-by|x-bootcamp-demo|x-environment|alt-svc|x-response-date|x-cache-tags|content-type):"
```

**Expected**:
- `X-Powered-By: Kong-Gateway`  (plugin *adds* this value, overriding whatever upstream sent)
- `X-Bootcamp-Demo: true`
- `X-Environment: bootcamp`
- `X-Response-Date: <timestamp>` (renamed from `Date`)
- `Content-Type: application/json; charset=utf-8` (replaced)
- `X-Cache-Tags: kong-gateway` (appended)
- *No* `Alt-Svc:` header (stripped by the remove rule).
- *No* `Date:` header (renamed to `X-Response-Date`).

> **Note:** Kong's own `Server` and `Via` headers are injected by Kong core
> *after* plugins run and **cannot** be removed by the Response Transformer
> plugin. To suppress them, set `headers = off` in `kong.conf` (not available
> on Konnect Serverless data planes).

---

## Step 13 - HTTP Log

Stream a JSON log entry to an external endpoint after every proxied
request. The bootcamp uses [webhook.site](https://webhook.site) so you can see
log lines arrive in your browser in real time.

> **Before applying:** open [webhook.site](https://webhook.site), copy your
> unique URL, and substitute it into the `HTTP Endpoint` field below.
> Never leave the literal `<YOUR-UNIQUE-ID>` placeholder in a real config.

### 13.1 Add the HTTP Log plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Logging → HTTP Log**
2. Configure:
   - **HTTP Endpoint**: `https://webhook.site/<YOUR-UNIQUE-ID>`
     (paste your real webhook.site URL - do **not** leave the placeholder)
   - **Method**: `POST`
   - **Content Type**: `application/json`
   - **Timeout**: `10000`
   - **Keepalive**: `60000`
   - **Flush Timeout**: `2`
   - **Retry Count**: `3`
3. **Scope**: `Service` → `httpbun-service`
4. Click **Save**

### 13.2 Test - logs appear at webhook.site

```bash
curl -s $PROXY_URL/httpbun/get > /dev/null
curl -s $PROXY_URL/httpbun/get > /dev/null
curl -s $PROXY_URL/httpbun/get > /dev/null
```

**Expected**: Three JSON entries land in your webhook.site inbox within
a few seconds, each containing the full Kong log object (request,
response, latencies, route, service, consumer).

> **Note:** The serverless DP runs in Konnect's cloud, so any log endpoint must
> be publicly reachable. Use webhook.site or a public endpoint for this demo.

---

## Step 14 - Consumer Groups + ACL

The capstone demo: combine three Kong features to build a tiered API
access system on `httpbun-service`.

1. **Key Auth** - identifies *who* is calling (authentication)
2. **ACL (Access Control List)** - decides *if* they're allowed (authorization)
3. **Consumer Groups** - applies *different rate limits per tier* (policy)

![Kong Consumer Flow](assets/kong_auth_flow.png)

> **Key concept:** ACL group ≠ Consumer Group.
> - **ACL group** (e.g., `premium`) → used by the ACL plugin for authorization
> - **Consumer Group** (e.g., `premium-tier`) → used for group-scoped rate limiting
> - A consumer can belong to both, independently

> **Reset first:** if Step 5 / Step 7 already added a `key-auth` plugin
> and other consumers to `httpbun-service`, delete them before starting
> this step so the only auth path is the one you build below.

### 14.1 Add Key Auth to httpbun-service

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Authentication → Key Authentication**
2. Configure:
   - **Key Names**: `apikey`
   - **Hide Credentials**: `on`
3. **Scope**: `Service` → `httpbun-service`
4. Click **Save**

### 14.2 Add ACL to httpbun-service

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Security → ACL**
2. Configure:
   - **Allow**: `premium`, `standard`
   - **Hide Groups Header**: `off`
3. **Scope**: `Service` → `httpbun-service`
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
   - **Group**: `trial` *(NOT in the ACL allow list - this consumer will get `403`)*
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

In **Gateway Services → `httpbun-service` → Plugins** you should see
`key-auth` and `acl` (the rate-limiting plugins live on the consumer
groups, not the service).

In **Consumers** you should see `premium-user`, `standard-user`,
`trial-user`. Open each one and confirm:

- `premium-user` → Credentials: `premium-key-123` · ACLs: `premium` · Groups: `premium-tier`
- `standard-user` → Credentials: `standard-key-456` · ACLs: `standard` · Groups: `standard-tier`
- `trial-user` → Credentials: `blocked-key-789` · ACLs: `trial` · Groups: *(none)*

In **Consumer Groups**:
- `premium-tier` - 1 member · rate-limiting `1000/min`
- `standard-tier` - 1 member · rate-limiting `10/min`

### 14.9 Test - no key

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `401 Unauthorized`.

### 14.10 Test - premium tier (high limit)

```bash
curl -i $PROXY_URL/httpbun/get -H "apikey: premium-key-123"
```

**Expected**: `200` with headers:
- `X-RateLimit-Limit-Minute: 1000`
- `X-Consumer-Username: premium-user`
- `X-Consumer-Groups: premium-tier`

### 14.11 Test - standard tier (low limit)

```bash
curl -i $PROXY_URL/httpbun/get -H "apikey: standard-key-456"
```

**Expected**: `200` with:
- `X-RateLimit-Limit-Minute: 10`
- `X-Consumer-Username: standard-user`
- `X-Consumer-Groups: standard-tier`

### 14.12 Test - trial tier (authenticated but blocked)

```bash
curl -i $PROXY_URL/httpbun/get -H "apikey: blocked-key-789"
```

**Expected**: `403` with body `{"message":"You cannot consume this service"}` —
key-auth passes (the key is valid), but ACL blocks the `trial` group.

### 14.13 Test - standard tier exceeds its limit

```bash
for i in $(seq 1 12); do
  code=$(curl -s -o /dev/null -w "%{http_code}" $PROXY_URL/httpbun/get \
    -H "apikey: standard-key-456")
  echo "Request $i: HTTP $code"
done
```

**Expected**: First 10 → `200`, then `429` as the consumer-group rate
limit kicks in. (Reset the counter by waiting 60 seconds.)

### 14.14 Test - httpbun still open

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `200` - all the Step 14 plugins are scoped to `httpbun-service`.

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

## Step 15 - Kong Identity (Konnect-native M2M)

Steps 5 (key-auth) and 6 (JWT) used credentials Kong stores itself. The next
step up is delegating identity to an **OAuth2 / OpenID Connect** provider - and
the simplest place to start is **Kong Identity**
([developer.konghq.com/identity](https://developer.konghq.com/identity/)), a
**regional OAuth2 / OIDC authorization server hosted inside Konnect**. You get
machine-to-machine auth **without running any IdP**: create the auth server and
client in the Konnect UI, and the same OpenID Connect plugin validates the
tokens it issues. (Step 16 then swaps in a full external IdP, Auth0, for
browser SSO and user login.)

| | Kong Identity (this step) | Auth0 (Step 16) |
|---|---|---|
| Where the IdP runs | Konnect-hosted, regional | Auth0 cloud tenant |
| Best for | Service-to-service (M2M) tokens | Browser SSO + user login |

### 15.1 Create the auth server

1. Go to **Konnect → Identity → Auth Servers**
2. Click **New Auth Server**, pick your **region**, Save
3. Copy the **Issuer URL** shown on the auth server's page
   - It follows the pattern `https://<id>.<region>.identity.konghq.com/auth`
   - Confirm it works: `curl -s <issuer-url>/.well-known/openid-configuration | jq .issuer`
   - Note the `/auth` suffix - the discovery doc lives at `<issuer>/auth/.well-known/openid-configuration`, **not** at the bare hostname

### 15.2 Create a client

1. **Konnect → Identity → Clients → New Client**
2. Configure:
   - **Grant type**: `client_credentials`
   - **Scopes**: add one, e.g. `api:read`
3. Save and copy the **Client ID** and **Client Secret**

### 15.3 Add the OpenID Connect plugin (validating Kong Identity)

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Authentication → OpenID Connect**
2. Configure:
   - **Issuer**: *(the Kong Identity Issuer URL from 15.1)*
   - **Client ID** / **Client Secret**: *(from 15.2)*
   - **Auth Methods**: `bearer`, `client_credentials`
   - **Scopes**: `openid`
3. **Scope**: `Service` → `httpbun-service`
4. Click **Save**

### 15.4 Test - the M2M flow

```bash
ISSUER=<your-kong-identity-issuer-url>   # e.g. https://<id>.<region>.identity.konghq.com/auth
CID=<your-client-id>
CSECRET=<your-client-secret>

# 0. Discover the token endpoint (one-time)
curl -s "$ISSUER/.well-known/openid-configuration" | jq .token_endpoint
# → should print something like https://<id>.<region>.identity.konghq.com/auth/oauth/token

# 1. Service mints a token from Kong Identity
TOKEN=$(curl -s -X POST "$ISSUER/oauth/token" \
  -d 'grant_type=client_credentials' \
  -d "client_id=$CID" -d "client_secret=$CSECRET" | jq -r .access_token)
echo $TOKEN   # sanity-check: should be a long JWT string, not "null"

# 2. Call Kong with that token → 200
curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"

# 3. No token → 401
curl -i $PROXY_URL/httpbun/get
```

> **Common pitfall:** the token endpoint is `/auth/oauth/token` (not
> `/auth/oauth2/token`). If you get a `404`, confirm the path from the
> discovery document.

**Expected**: `200` with a token, `401` without.

> **Clean up:** delete the OpenID Connect plugin from `httpbun-service`.

---

## Step 16 - OpenID Connect with Auth0 (AuthN / AuthZ)

Kong Identity (Step 15) is Konnect-hosted. When you instead need to integrate
your **own corporate IdP** - Okta, Entra ID, Auth0, Ping, or Keycloak - you point
the same **OpenID Connect** plugin at that external provider. Here you protect
`httpbun-service` with **Auth0**, which also unlocks the **browser SSO
(Authorization Code)** flow with real users.

### 16.0 Set up Auth0

1. **Create an Auth0 tenant** at [auth0.com](https://auth0.com) (free tier works)
2. **Create a Regular Web Application:**
   - Auth0 Dashboard → Applications → Create Application → Regular Web Application
   - Note the **Domain** (`<AUTH0_DOMAIN>`), **Client ID** (`<AUTH0_CLIENT_ID>`),
     and **Client Secret** (`<AUTH0_CLIENT_SECRET>`)
   - Under Settings → Allowed Callback URLs, add:
     `$PROXY_URL/httpbun/auth/callback`
   - Under Settings → Advanced Settings → Grant Types, enable **Password** grant
3. **Create test users** in Auth0 → User Management → Users:

   | Email | Password | Nickname |
   |---|---|---|
   | `alice@bootcamp.dev` | `AlicePassword1!` | `alice` |
   | `bob@bootcamp.dev` | `BobPassword1!` | `bob` |

4. **Create an API** (optional, for `client_credentials` flow):
   - Auth0 Dashboard → Applications → APIs → Create API
   - Set an **Identifier** (audience), e.g. `https://<AUTH0_DOMAIN>/api/v2/`

### 16.1 Add the OpenID Connect plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Authentication → OpenID Connect**
2. Configure **Discovery / Auth**:
   - **Issuer**: `https://<AUTH0_DOMAIN>/`
   - **Client ID**: `<AUTH0_CLIENT_ID>`
   - **Client Secret**: `<AUTH0_CLIENT_SECRET>`
   - **Auth Methods**: `password`, `bearer`, `client_credentials`
   - **Scopes**: `openid`, `profile`, `email`
   - **Login Action**: `response`
   - **Cache Tokens Salt**: `bootcamp-oidc-salt-change-me`
   - **Redirect URI**: `$PROXY_URL/httpbun/auth/callback`
   - **Logout URI Suffix**: `/logout`
3. Configure **Upstream Headers** (forwards identity claims to the upstream):
   - **Upstream Access Token Header**: `authorization`
   - **Upstream Headers Claims**: `nickname`, `email`
   - **Upstream Headers Names**: `x-authenticated-user`, `x-authenticated-email`
4. **Scope**: `Service` → `httpbun-service`
5. Click **Save**

> **Note:** Auth0 uses `nickname` (not Keycloak's `preferred_username`) as the
> default username claim. To use `preferred_username`, add a custom Auth0 Action
> that injects it into the token.

### 16.2 Test - no token is rejected

```bash
curl -i $PROXY_URL/httpbun/get
```

**Expected**: `401 Unauthorized`.

### 16.3 Test - valid bearer token is accepted

```bash
TOKEN=$(curl -s --request POST \
  --url https://<AUTH0_DOMAIN>/oauth/token \
  --header 'content-type: application/json' \
  --data '{"client_id":"<AUTH0_CLIENT_ID>","client_secret":"<AUTH0_CLIENT_SECRET>","audience":"https://<AUTH0_DOMAIN>/api/v2/","grant_type":"client_credentials"}' | jq -r '.access_token')

curl -i $PROXY_URL/httpbun/get -H "Authorization: Bearer $TOKEN"
```

**Expected**: `200` - the OIDC plugin validated the token against Auth0's JWKS.

### 16.4 (optional) Full browser login

Edit the plugin: set **Auth Methods** to `authorization_code`, `bearer`,
`session` and **Login Action** to `redirect`, Save. Open
`$PROXY_URL/httpbun/get` in a browser → you're redirected to the
Auth0 Universal Login page → sign in as **alice@bootcamp.dev / AlicePassword1!** →
redirected back with a session cookie and the upstream `200`.

### 16.5 (optional) Token introspection - real-time revocation

So far Kong validates the JWT **offline** against Auth0's JWKS - fast, no
per-request call to the IdP, but a token stays valid until it expires even after
revocation. **Introspection** ([RFC 7662](https://www.rfc-editor.org/rfc/rfc7662))
makes Kong call Auth0's introspect endpoint on every request to ask "is this
token still active?", so revocation takes effect immediately (and it works for
opaque, non-JWT tokens too).

| | Local JWKS validation (default) | Introspection |
|---|---|---|
| Per-request cost | None (verifies signature locally) | One call to Auth0 |
| Revocation honoured | Only at token expiry | Immediately |
| Works with opaque tokens | No (JWT only) | Yes |

**Switch the plugin to introspection** - edit the OpenID Connect plugin on
`httpbun-service` and set:

- **Introspection Endpoint**: `https://<AUTH0_DOMAIN>/oauth/introspect`
- **Introspect JWT Tokens**: `on` (introspect even JWT access tokens)
- **Introspection Endpoint Auth Method**: `client_secret_basic`
- **Cache Introspection**: `off` (demo - so revocation is instant)

Save. (Client ID/Secret are already set, and Auth0 reuses them to authenticate
the introspection call.)

With the **default** (offline JWKS) config, a revoked token would still return
`200` until it expired - that's the difference introspection makes.

> **Clean up:** delete the OpenID Connect plugin from `httpbun-service`.

---

## Step 17 - Upstream OAuth (Kong as the OAuth client)

Steps 15 and 16 made Kong **validate** tokens coming *from* callers.
[Upstream OAuth](https://developer.konghq.com/plugins/upstream-oauth/) is the
**mirror image**: Kong fetches a `client_credentials` token from the IdP and
injects it as `Authorization: Bearer …` on the **upstream** request - so a
protected backend gets a valid machine-to-machine token while the caller sends
no auth at all.

You'll scope it to `httpbun-service`, whose `/headers` echoes what the upstream
received, using an Auth0 Machine-to-Machine application.

> **No `iss` matching here** - Kong is the OAuth *client*, not the validator, so
> it just forwards the token. You only need the token endpoint reachable from the
> serverless DP (Auth0 is public, so this works out of the box).

#### Auth0 Setup

1. **Create a Machine-to-Machine application** in Auth0 Dashboard → Applications
2. **Authorize it** against your API (audience)
3. Note the **Client ID** (`<AUTH0_M2M_CLIENT_ID>`) and **Client Secret** (`<AUTH0_M2M_CLIENT_SECRET>`)

### 17.1 Add the Upstream OAuth plugin

1. **Gateway Services → `httpbun-service` → Plugins → New Plugin → Upstream OAuth**
2. Configure (under **Config → Oauth**):
   - **Token Endpoint**: `https://<AUTH0_DOMAIN>/oauth/token`
   - **Client ID**: `<AUTH0_M2M_CLIENT_ID>`
   - **Client Secret**: `<AUTH0_M2M_CLIENT_SECRET>`
   - **Grant Type**: `client_credentials`
   - **Scopes**: `openid`
3. Under **Config → Client**:
   - **Auth Method**: `client_secret_post`
4. Under **Config → Behavior**:
   - **Upstream Access Token Header Name**: `Authorization`
   - **Purge Token On Upstream Status Codes**: `401`
5. Under **Config → Cache**:
   - **Strategy**: `memory`
   - **Default TTL**: `3600`
   - **Eagerly Expire**: `5` (re-fetch 5 s before token expiry)
6. **Scope**: `Service` → `httpbun-service`
7. Click **Save**

### 17.2 Test - the caller sends nothing, the upstream sees a token

```bash
# Client sends NO Authorization header
curl -s $PROXY_URL/httpbun/headers | jq '.headers.Authorization'
```

**Expected**: `"Bearer eyJhbGciOi..."` - Kong obtained this from Auth0 using
the M2M app and attached it to the upstream call.

```bash
# Decode it to prove it's a real M2M token
curl -s $PROXY_URL/httpbun/headers | jq -r '.headers.Authorization' \
  | cut -d' ' -f2 | cut -d. -f2 | base64 -d 2>/dev/null | jq '{iss, azp, typ}'
```

**Expected**: `azp: "<AUTH0_M2M_CLIENT_ID>"`, `iss: "https://<AUTH0_DOMAIN>/"`.
Kong caches the token (`default_ttl: 3600`) and auto-refreshes near expiry
(`eagerly_expire: 5` means it re-fetches 5 seconds before the token expires),
so it isn't hitting Auth0 on every request.

> **Clean up:** delete the Upstream OAuth plugin from `httpbun-service`.

---

## Cleanup

To reset back to the base topology of Step 1 (one service + one route):

1. **Gateway Manager → `<your-control-plane>` → Plugins** - delete each plugin
   you added (`rate-limiting`, `proxy-cache`, `key-auth`, `jwt`, `cors`,
   `ip-restriction`, `correlation-id`, `request-transformer`,
   `response-transformer`, `http-log`, `acl`, `openid-connect`,
   `upstream-oauth`)
2. **Consumers** - delete `demo-user`, `test-user`, `jwt-user`, `alice`,
   `bob`, `charlie`, `premium-user`, `standard-user`, `trial-user`
3. **Consumer Groups** - delete `premium-tier`, `standard-tier`
4. **Upstreams** - delete `demo-upstream`
5. **Gateway Services** - delete `loadbalanced-service` (cascades to its route)
6. Leave `httpbun-service` in place if you want to keep the base topology;
   otherwise delete it too.

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
| `403 Your IP address is not allowed` | Your public IP is not in the allow list - check your IP with `curl -s httpbun.com/ip` and add the appropriate CIDR |
| `429` immediately on first request | Step 2 (per-IP) and Step 14 (per-consumer-group) limits stack - disable one when testing the other |
| `X-Cache-Status: Bypass` on a `GET` | Method/content-type must be in the Proxy Cache config - check `request_method` and `content_type` |
| `403 You cannot consume this service` with a valid key | ACL plugin allow list doesn't include the consumer's ACL group - re-check Step 14.2 |
| HTTP Log shows nothing at webhook.site | The endpoint URL still has `<YOUR-UNIQUE-ID>` - paste your real webhook.site URL. Endpoint must be publicly reachable for serverless DPs |
| Round-robin not alternating | Send 4+ requests; check `.url` field to confirm the upstream actually changes |
| Plugin not visible in UI | Confirm Kong Gateway data plane is 3.7+; some plugin names differ slightly across versions |
| `no Route matched` after a UI save | Wait 5-10 seconds for config to propagate to the data plane, then retry |
| Auth0 `invalid_grant` | Wrong credentials or grant not enabled - verify client ID/secret; ensure password grant is enabled under Application → Advanced → Grant Types |
| Auth0 `consent_required` | API audience not authorized - authorize the application against the API in Auth0 Dashboard → APIs |
| Auth0 `audience mismatch` | Wrong audience in token request - verify the `audience` parameter matches your Auth0 API identifier |
