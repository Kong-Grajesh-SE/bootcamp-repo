# Kong Developer Portal Bootcamp — Bookstore API

> **Story:** You built a Bookstore API spec in the APIOps bootcamp. Now you'll
> convert it to Kong Gateway config, deploy it, publish it on a Developer Portal,
> and walk through the full developer self-service experience — from registration
> to making authenticated API calls.

> **CLI ↔ UI:** This guide is **dual-track by step**. Every Konnect API call
> below is paired with its **"Via Konnect UI"** block, so you can choose
> click-by-click navigation or the curl/API path at each step. There is no
> separate `README-UI.md` — the UI walkthrough lives inline here.

> **What you bring forward from the previous modules:** The
> `openapi/bookstore-api.yaml` here is the **same file** you used in apiops
> — that's deliberate. The `deck file openapi2kong`, `deck file patch`, and
> `deck file add-plugins` commands all come back. New here are the Konnect
> **Catalog** and **Dev Portal** concepts (API product, version, publication,
> auth strategy, application) — the table after the "Part 2" heading
> defines each before they're first used.

---

## The Flow

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  OpenAPI Spec    │────▶│  deck file       │────▶│  deck gateway    │
│  bookstore-api   │     │  openapi2kong    │     │  sync            │
│  .yaml           │     │  + add-plugins   │     │  (deploy to CP)  │
└──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                           │
                    ┌──────────────────────────────────────┘
                    ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Create API      │────▶│  Publish to      │────▶│  Developer       │
│  Product in      │     │  Portal with     │     │  registers, gets │
│  Konnect         │     │  auth strategy   │     │  key, calls API  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## Prerequisites

- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- Konnect account at [cloud.konghq.com](https://cloud.konghq.com)
- Konnect Personal Access Token (PAT)
- A control plane with a connected data plane
- `curl` and `jq` installed
- Terminal open in this `api-portal/` directory

```bash
export KONNECT_TOKEN="<your-konnect-pat>"
export CP_NAME="<your-control-plane-name>"
export PROXY_URL=http://localhost:8000

export KONNECT_PAT="$KONNECT_TOKEN"
export KONNECT_API="https://us.api.konghq.com"
```

> **Geo URL:** Use `us.api.konghq.com`, `eu.api.konghq.com`, or `au.api.konghq.com`
> to match where your org is hosted.

Verify access:

```bash
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v2/users/me" | jq '{name: .full_name, email}'

curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v2/organizations/me" | jq '{org: .name, state}'
```

---

## File Structure

```
api-portal/
├── openapi/
│   └── bookstore-api.yaml       ← Same spec from APIOps bootcamp
├── deck/
│   └── plugin-cors.yaml          ← CORS plugin (required for portal "Try It")
├── pages/
│   ├── getting-started.md       ← Portal page content
│   ├── terms-of-service.md      ← Portal page content
│   └── changelog.md             ← Portal page content
├── docs/
│   └── books-quickstart.md      ← API-level documentation
└── README.md                    ← This file
```

---

# Part 1 — Deploy the Bookstore API to Gateway

> You start with an OpenAPI spec. Using decK's APIOps commands, you'll convert it
> to Kong config, add CORS, and deploy — all without writing YAML by hand.
>
> **Important:** Do NOT add a `key-auth` plugin via decK when using portal auth
> strategies. Konnect auto-creates a `konnect-application-auth` plugin when you
> attach an auth strategy in Step 12. Adding your own `key-auth` plugin creates a
> conflict that rejects portal-issued keys.

---

## Step 1 — Convert OpenAPI to Kong Config

> **What it does:** `deck file openapi2kong` reads your OpenAPI spec and generates
> Kong services and routes automatically. The `servers` URL becomes the upstream,
> and each path becomes a route.

```bash
deck file openapi2kong \
  --spec openapi/bookstore-api.yaml \
  --output-file deck/generated-kong.yaml
```

**Inspect what was generated:**

```bash
cat deck/generated-kong.yaml
```

You'll see a Kong service pointing at `https://httpbin.org` (from the spec's `servers` block)
with routes for `/books`, `/books/{bookId}`, `/authors`, `/authors/{authorId}`, and `/reviews`.

> **Why we need one small patch:** The Bookstore spec is shared with the APIOps
> bootcamp, where the upstream is `https://httpbin.org` (clean and product-y).
> But httpbin.org itself doesn't have `/books`, `/authors`, etc. — only its
> `/anything` endpoint echoes arbitrary paths back as JSON. So we use
> `deck file patch` (same command from APIOps Step 14) to set the service's
> `path` to `/anything` without editing the spec:

```bash
deck file patch \
  --selector '$..services[*]' \
  --value 'path:"/anything"' \
  -s deck/generated-kong.yaml \
  --output-file deck/generated-kong.yaml
```

Now every request through Kong is rewritten to `https://httpbin.org/anything/<route>`,
which httpbin will echo back as JSON — perfect for demonstrating the gateway and
auth flow without standing up a real Bookstore backend.

---

## Step 2 — Add CORS Plugin

> **What it does:** `deck file add-plugins` layers the CORS plugin onto the generated
> config — no manual YAML editing needed. This is the APIOps way.
> CORS is required for the Dev Portal's "Try It" feature to make cross-origin
> requests to your Kong proxy.
>
> **Why no key-auth here?** Auth is handled by Konnect's portal auth strategy
> (Step 12). When you attach a key-auth strategy to a publication, Konnect
> auto-creates a `konnect-application-auth` plugin on the gateway service.
> Adding a manual `key-auth` plugin via decK would conflict with it.

```bash
deck file add-plugins \
  -s deck/generated-kong.yaml \
  deck/plugin-cors.yaml \
  --output-file deck/bookstore-final.yaml
```

**Verify the CORS plugin was added:**

```bash
grep "name: cors" deck/bookstore-final.yaml
```

---

## Step 3 — Validate Before Deploying

```bash
# Offline validation
deck file validate deck/bookstore-final.yaml

# Validate against live Kong
deck gateway validate deck/bookstore-final.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

---

## Step 4 — Preview Changes (diff)

```bash
deck gateway diff deck/bookstore-final.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

You'll see the services, routes, and CORS plugin that will be created.

---

## Step 5 — Deploy to Gateway (sync)

```bash
deck gateway sync deck/bookstore-final.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Verify the routes are live:**

```bash
# No auth yet → request reaches upstream (httpbin echoes back the request as JSON)
curl -i $PROXY_URL/books
# → 200 from httpbin.org/anything (via Kong) — the route is working
# Auth will be enforced after attaching the portal auth strategy in Step 12
```

> **Konnect UI verification:**
> ```
> Gateway Manager → your-control-plane → Services
>   → You should see the bookstore service with routes for /books, /authors, /reviews
>
> Gateway Manager → your-control-plane → Plugins
>   → CORS plugin attached to the service
> ```

---

## Step 5b — Verify in Konnect UI (Step-by-Step)

```
1. Log in to cloud.konghq.com
2. Left sidebar → Gateway Manager
3. Click your control plane (your-control-plane)
4. Click Services in the left menu
   → You should see the bookstore service (name comes from your OpenAPI title)
5. Click the service → Routes tab
   → Routes for /books, /books/{bookId}, /authors, /authors/{authorId}, /reviews
6. Click Plugins in the left menu
   → CORS plugin listed, scoped to the bookstore service
```

---

# Part 2 — Create the Developer Portal & Publish the API

> Now that the Bookstore API is running on the gateway with CORS enabled,
> you need a way for external developers to discover it, register, and get API keys.
> Auth will be enforced automatically when you attach an auth strategy to the publication.

### Concepts you'll meet in Part 2 — read this once

Part 1 was familiar territory (OpenAPI → decK → gateway). Part 2 introduces
Konnect's API Catalog and Dev Portal model. The same concepts come back over
and over — keep this table handy.

| Concept | What it is | Where it appears |
|---|---|---|
| **API Product** | The umbrella catalog entry for one logical API. Holds versions, specs, and implementations. | Step 7 creates it. |
| **API Version** | A versioned snapshot of the product (`1.0.0`, `2.0.0`) that owns its own spec. | Step 8 creates one. |
| **Spec** | The OpenAPI document attached to a version. | Step 8 uploads it. |
| **Implementation** | The link between an API product and a live gateway service that fulfils requests. | Step 9 creates it. |
| **Portal** | The developer-facing website (registration, docs, "Try It"). | Step 6 creates it. |
| **Publication** | The decision to make a specific API product visible on a specific portal, with a visibility level and an auth strategy. | Step 10 creates one. |
| **Auth Strategy** | The contract for how registered apps authenticate (key-auth, OIDC). Attached to a publication. | Step 11 creates one; Step 12 attaches it. |
| **Application** | A developer-owned "client" that gets credentials issued against an auth strategy. | Step 16 creates one. |
| **Visibility** | Per-publication: `public` (anyone with the portal URL sees the API listing) vs `private` (login required). | Step 10 sets it. |
| **`konnect-application-auth`** | The gateway plugin Konnect auto-creates when you attach an auth strategy. *Don't add your own key-auth alongside — it conflicts.* | Created behind the scenes in Step 12. |

> **Mental model:** *Product* is the noun in the catalog. *Publication* is
> the verb that puts it on a portal. *Implementation* is what makes a call
> actually land on Kong. *Auth Strategy* is the lock on the door.

---

## Step 6 — Create the Developer Portal

### Via Konnect UI

```
1. Left sidebar → Dev Portal
2. Click New Portal
3. Fill in:
   - Name: bookstore-portal
   - Display Name: Bookstore Developer Portal
   - Description: Browse and manage books, authors, and reviews
4. Leave Authentication enabled (default)
5. Click Create
```

### Via Konnect API

```bash
curl -s -X POST "$KONNECT_API/v3/portals" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bookstore-portal",
    "display_name": "Bookstore Developer Portal",
    "description": "Browse and manage books, authors, and reviews",
    "authentication_enabled": true,
    "auto_approve_developers": false,
    "auto_approve_applications": false,
    "default_api_visibility": "public",
    "default_page_visibility": "public"
  }' | jq '{id, name, default_domain}'
```

Save the portal ID:

```bash
export PORTAL_ID=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals" | jq -r '.data[] | select(.name=="bookstore-portal") | .id')
echo "Portal ID: $PORTAL_ID"
```

**Checkpoint:** Open the portal URL to see what the **default portal** looks like (empty, no APIs yet):

```bash
PORTAL_URL=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID" | jq -r '.default_domain')
echo "Open: https://$PORTAL_URL"
```

> Open this URL in your browser. You'll see a clean, empty portal with the Konnect default
> theme. No APIs listed yet — that's what we'll fix next.

---

## Step 7 — Create an API Product

An API Product is the catalog entry developers see. It wraps your spec, version, and
gateway link into one publishable unit.

### Via Konnect UI

```
1. Left sidebar → API Products
2. Click Add API Product
3. Fill in:
   - Name: Bookstore API
   - Description: Browse and manage books, authors, and reviews
4. Click Save
```

### Via Konnect API

```bash
curl -s -X POST "$KONNECT_API/v3/apis" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bookstore-api",
    "description": "Browse and manage books, authors, and reviews"
  }' | jq '{id, name}'
```

```bash
export BOOKSTORE_API_ID=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis" | jq -r '.data[] | select(.name=="bookstore-api") | .id')
echo "API Product ID: $BOOKSTORE_API_ID"
```

---

## Step 8 — Upload the OpenAPI Spec as a Version

### Via Konnect UI

```
1. API Products → Bookstore API
2. Click Versions tab → Add Version
3. Name: v1.0.0
4. Upload spec: select openapi/bookstore-api.yaml
5. Click Save
```

### Via Konnect API

```bash
curl -s -X POST "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/versions" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg spec "$(cat openapi/bookstore-api.yaml)" '{
    "name": "v1.0.0",
    "spec": {
      "content": $spec
    }
  }')" | jq '{id, name}'
```

**Checkpoint:**

```bash
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/versions" | jq '.data[] | {name, id}'
```

---

## Step 9 — Link to Gateway Service (Implementation)

This connects the API product to the actual running service on your control plane.
Without this, the portal's "Try It" feature won't know where to send requests.

### Via Konnect UI

```
1. API Products → Bookstore API
2. Click Implementations tab → Add Implementation
3. Select your control plane (your-control-plane)
4. Select the bookstore service (created by openapi2kong)
5. Click Save
```

### Via Konnect API

```bash
# Find control plane ID
export CP_ID=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v2/control-planes" | jq -r '.data[] | select(.name=="'$CP_NAME'") | .id')
echo "CP ID: $CP_ID"

# Find the gateway service ID
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v2/control-planes/$CP_ID/core-entities/services" | \
  jq '.data[] | {id, name}'
```

```bash
# Capture the bookstore service ID. The service name comes from your OpenAPI
# `info.title` (slugified by openapi2kong) — adjust the filter below if you
# renamed the spec. Filtering by name (instead of `.data[0]`) is important
# when the control plane already has services from earlier bootcamps.
export BOOKSTORE_SVC_ID=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v2/control-planes/$CP_ID/core-entities/services" | \
  jq -r '.data[] | select(.name | test("bookstore")) | .id' | head -n1)
echo "Service ID: $BOOKSTORE_SVC_ID"
[ -z "$BOOKSTORE_SVC_ID" ] && echo "ERROR: bookstore service not found — did Step 8 sync run?" && return 1 2>/dev/null
```

```bash
# Create the implementation
curl -s -X POST "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/implementations" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"kong-service\",
    \"service_reference\": {
      \"service\": {
        \"id\": \"$BOOKSTORE_SVC_ID\",
        \"control_plane_id\": \"$CP_ID\"
      }
    }
  }" | jq '{id, type}'
```

**Checkpoint:**

```bash
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/implementations" | \
  jq '.data[] | {id, type}'
```

---

## Step 10 — Publish API to the Portal

### Via Konnect UI

```
1. API Products → Bookstore API
2. Click Portal Publishing tab
3. Click Publish to Portal
4. Select bookstore-portal → Visibility: Public → Click Publish
```

### Via Konnect API

```bash
curl -s -X POST "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/publications" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "{
    \"portal_id\": \"$PORTAL_ID\",
    \"visibility\": \"public\",
    \"auto_approve_registrations\": true
  }" | jq '{id, visibility}'
```

**Checkpoint — Browse the portal again:**

```bash
PORTAL_URL=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID" | jq -r '.default_domain')
echo "Open: https://$PORTAL_URL"
```

> Open in browser. Now you should see the **Bookstore API** card in the catalog.
> Click into it — the full OpenAPI spec renders with interactive docs showing
> all endpoints: `/books`, `/authors`, `/reviews`.

---

# Part 3 — Configure Auth & Developer Self-Service

> The API is published but developers can't get credentials yet.
> You need an auth strategy and self-service configuration.

---

## Step 11 — Create a Key Auth Strategy

### Via Konnect UI

```
1. Left sidebar → Application Auth
2. Click New Auth Strategy
3. Fill in:
   - Name: bookstore-key-auth
   - Display Name: API Key Authentication
   - Strategy Type: Key Auth
   - Key Names: apikey
4. Click Save
```

### Via Konnect API

```bash
curl -s -X POST "$KONNECT_API/v3/application-auth-strategies" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bookstore-key-auth",
    "display_name": "API Key Authentication",
    "strategy_type": "key_auth",
    "configs": {
      "key_auth": {
        "key_names": ["apikey"]
      }
    }
  }' | jq '{id, name, strategy_type}'
```

```bash
export AUTH_STRATEGY_ID=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/application-auth-strategies" | \
  jq -r '.data[] | select(.name=="bookstore-key-auth") | .id')
echo "Auth Strategy: $AUTH_STRATEGY_ID"
```

---

## Step 12 — Attach Auth Strategy to the Publication

### Via Konnect UI

```
1. API Products → Bookstore API → Portal Publishing tab
2. Click the publication entry (bookstore-portal)
3. Under Auth Strategy, select "API Key Authentication"
4. Click Save
```

### Via Konnect API

```bash
PUB_ID=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/publications" | jq -r '.data[0].id')

curl -s -X PATCH "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/publications/$PUB_ID" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "{
    \"auth_strategy_ids\": [\"$AUTH_STRATEGY_ID\"]
  }" | jq '{id, auth_strategy_ids}'
```

---

## Step 13 — Enable Developer Auto-Approve (Lab Environment)

### Via Konnect UI

```
1. Dev Portal → bookstore-portal → Settings
2. Set:
   - Auto Approve Developers: enabled ✅
   - Auto Approve Applications: enabled ✅
3. Click Save
```

### Via Konnect API

```bash
curl -s -X PATCH "$KONNECT_API/v3/portals/$PORTAL_ID" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_approve_developers": true,
    "auto_approve_applications": true
  }' | jq '{auto_approve_developers, auto_approve_applications}'
```

> **Production note:** Set both to `false` in production. Use auto-approve only for
> labs and internal portals.

| Setting | `true` | `false` |
|---------|--------|---------|
| `auto_approve_developers` | Developer browses immediately after sign-up | Admin must approve first |
| `auto_approve_applications` | App gets credentials immediately | Admin must approve first |

---

## Step 13b — Register Proxy URL (Required for Portal "Try It")

The portal's "Try It" panel runs in the browser and needs to know where your
data plane proxy is. Set the proxy URL on your control plane:

### Via Konnect UI

```
1. Gateway Manager → your-control-plane → Overview
2. Under Proxy URL, click Add Endpoint
3. Enter:
   - Protocol: http (or https if using TLS)
   - Host: localhost (or your public hostname)
   - Port: 8000
4. Click Save
```

### Via Konnect API

```bash
curl -s -X PATCH "$KONNECT_API/v2/control-planes/$CP_ID" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "proxy_urls": [
        {
          "host": "localhost",
          "port": 8000,
          "protocol": "http"
        }
      ]
    }
  }' | jq '.config.proxy_urls'
```

> **"Try It" limitations with local data planes:**
> The portal is hosted at `https://*.kongportals.com`. The "Try It" panel makes
> requests from your browser. If your data plane is on `localhost`, "Try It" will
> fail with **"Failed to fetch"** due to mixed content (HTTPS → HTTP) or the
> proxy being unreachable from other machines.
>
> **Options for a working "Try It":**
> - Use [ngrok](https://ngrok.com) to expose your local proxy: `ngrok http 8000`,
>   then update the proxy URL to the ngrok HTTPS hostname:
>   ```bash
>   # Start ngrok
>   ngrok http 8000
>   # Copy the https://*.ngrok-free.app URL, then update the proxy URL:
>   export NGROK_HOST="<your-subdomain>.ngrok-free.app"
>   curl -s -X PATCH "$KONNECT_API/v2/control-planes/$CP_ID" \
>     -H "Authorization: Bearer $KONNECT_PAT" \
>     -H "Content-Type: application/json" \
>     -d "{\"proxy_urls\": [{\"host\": \"$NGROK_HOST\", \"port\": 443, \"protocol\": \"https\"}]}"
>   ```
> - Use a cloud-hosted data plane with a public URL
> - Use Konnect Cloud Gateway (managed DP with built-in public URL)
>
> **For the bootcamp:** Test via `curl` in Step 18 — this always works regardless
> of proxy visibility.

---

# Part 4 — The Developer Experience (End-to-End)

> Now switch hats — you're an external developer discovering the Bookstore API
> for the first time.

---

## Step 14 — Browse the Portal as a Visitor

```bash
PORTAL_URL=$(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID" | jq -r '.default_domain')
echo "Open in incognito: https://$PORTAL_URL"
```

1. Open the URL in an **incognito/private browser window**
2. You see the **Bookstore API** in the catalog
3. Click into it — you can read the full API docs
4. But you can't use "Try It" or get credentials — you need to register

---

## Step 15 — Register as a Developer

```
1. Click Sign Up (or Register)
2. Fill in:
   - Full Name: Test Developer
   - Email: testdev@example.com
   - Password: (create one)
3. Click Create Account
4. With auto-approve enabled → you're logged in immediately
```

---

## Step 16 — Create an Application

```
1. Click My Apps (or user menu → Applications)
2. Click New Application
3. Fill in:
   - Name: bookstore-reading-app
   - Description: A reading list app that browses the book catalog
4. Click Create
```

---

## Step 17 — Register for the Bookstore API

```
1. Go to the API Catalog → click Bookstore API
2. Click Register (or Request Access)
3. Select your application: bookstore-reading-app
4. With auto-approve enabled → access is granted immediately
5. An API key is generated — copy it!
```

> **What just happened behind the scenes:**
> - Konnect created a **credential** for this application via the `konnect-application-auth` plugin
> - The API key is managed by Konnect's auth strategy — no manual consumer/credential creation needed
> - The `konnect-application-auth` plugin (auto-created in Step 12) validates the key at the gateway

---

## Step 18 — Make Authenticated API Calls

```bash
# Replace <PASTE-API-KEY-FROM-STEP-17> with the key the portal displayed
# in Step 17 (this is the ONLY time you can see the full value).
export DEV_API_KEY="<PASTE-API-KEY-FROM-STEP-17>"
export PROXY_URL=http://localhost:8000

# ✅ With key → proxied to upstream (httpbin echoes back the request as JSON)
curl -i -H "apikey: $DEV_API_KEY" $PROXY_URL/books
# → 200 OK with JSON echo (method, url, headers, origin)
# Look for: Via: kong, X-Kong-Upstream-Latency (proves it went through)

# ❌ Without key → 401 (blocked by konnect-application-auth)
curl -i $PROXY_URL/books
# → 401 Unauthorized

# ❌ Wrong key → 401 (invalid credential)
curl -i -H "apikey: wrong-key-123" $PROXY_URL/books
# → 401 Unauthorized

# ✅ Try other endpoints
curl -s -H "apikey: $DEV_API_KEY" $PROXY_URL/authors | jq .
curl -s -H "apikey: $DEV_API_KEY" $PROXY_URL/reviews | jq .

# ✅ Try a specific book ID
curl -s -H "apikey: $DEV_API_KEY" $PROXY_URL/books/1 | jq .
```

**Checkpoint:** Requests with a valid key return **200 OK** with a JSON echo from
httpbin.org/anything (showing method, URL, headers, origin). Requests without a key
or with a wrong key return **401 Unauthorized**. The portal auth strategy is working end-to-end.

> **Why httpbin.org/anything?** It echoes back every request as a JSON object —
> method, URL, headers, query params — making it easy to verify that auth passed
> and the request was proxied correctly through Kong.

---

## Step 19 — View as Admin (Back in Konnect)

### Via Konnect UI

```
1. Left sidebar → Dev Portal → bookstore-portal
2. Click Developers → you see "Test Developer" with status Approved
3. Click Applications → you see "bookstore-reading-app" with status Approved
4. Click into the app → see which APIs it has access to

5. Left sidebar → Gateway Manager → your-control-plane
6. Click Plugins → you see `konnect-application-auth` (auto-created by the auth strategy)
```

### Via Konnect API

```bash
# List developers on the portal
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/developers" | \
  jq '.data[] | {email, status, created_at}'

# List applications
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/applications" | \
  jq '.data[] | {name, id, created_at}'
```

---

# Part 5 — Customize the Portal

> The default portal works, but it looks generic. Let's customize it with
> branding, documentation pages, and a support snippet.

---

## Step 20 — Customize Appearance

### Via Konnect UI

```
1. Dev Portal → bookstore-portal → Settings → Appearance
2. Update:
   - Theme Mode: Dark
   - Primary Color: #8B4513 (bookstore brown)
3. Upload a logo (optional — any PNG/SVG)
4. Under Spec Renderer, enable:
   - Try It UI: ✅
   - Open in Insomnia: ✅
   - Show Schemas: ✅
5. Click Save
```

### Via Konnect API

```bash
curl -s -X PUT "$KONNECT_API/v3/portals/$PORTAL_ID/customization" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": {
      "name": "custom",
      "mode": "dark",
      "colors": {
        "primary": "#8B4513"
      }
    },
    "spec_renderer": {
      "try_it_ui": true,
      "try_it_insomnia": true,
      "show_schemas": true,
      "hide_internal": true,
      "hide_deprecated": true
    }
  }' | jq '{theme, spec_renderer}'
```

> **Refresh the portal** in your browser — you'll see the dark theme with bookstore brown accent.

---

## Step 21 — Add Portal Pages

Portal Pages are Markdown documents that appear alongside your API catalog — guides,
terms, changelogs. The content is in the `pages/` folder.

### 21a. Getting Started page

```bash
curl -s -X POST "$KONNECT_API/v3/portals/$PORTAL_ID/pages" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat pages/getting-started.md)" '{
    "title": "Getting Started",
    "slug": "/getting-started",
    "visibility": "public",
    "status": "published",
    "content": $content
  }')" | jq '{id, title, slug}'
```

### 21b. Terms of Service page

```bash
curl -s -X POST "$KONNECT_API/v3/portals/$PORTAL_ID/pages" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat pages/terms-of-service.md)" '{
    "title": "Terms of Service",
    "slug": "/terms-of-service",
    "visibility": "public",
    "status": "published",
    "content": $content
  }')" | jq '{id, title, slug}'
```

### 21c. Changelog page

```bash
curl -s -X POST "$KONNECT_API/v3/portals/$PORTAL_ID/pages" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat pages/changelog.md)" '{
    "title": "Changelog",
    "slug": "/changelog",
    "visibility": "public",
    "status": "published",
    "content": $content
  }')" | jq '{id, title, slug}'
```

**Verify:**

```bash
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/pages" | \
  jq '.data[] | {title, slug, status}'
```

> **Via Konnect UI:**
> ```
> Dev Portal → bookstore-portal → Pages
>   → You should see 3 pages: Getting Started, Terms of Service, Changelog
>   → Click any page to preview the rendered Markdown
> ```

---

## Step 22 — Add API-Level Documentation

API Documents attach directly to an API product (not the portal). They appear as
tabs alongside the OpenAPI spec.

```bash
curl -s -X POST "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/documents" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat docs/books-quickstart.md)" '{
    "title": "Quick Start Guide",
    "slug": "quick-start",
    "status": "published",
    "content": $content
  }')" | jq '{id, title, slug}'
```

> **Via Konnect UI:**
> ```
> API Products → Bookstore API → Documents tab
>   → "Quick Start Guide" listed
>   → On the portal, click Bookstore API → you'll see a "Quick Start" tab next to the spec
> ```

---

## Step 23 — Add a Support Snippet

Snippets are reusable content blocks shown in portal locations (banners, headers, footers).

```bash
curl -s -X POST "$KONNECT_API/v3/portals/$PORTAL_ID/snippets" \
  -H "Authorization: Bearer $KONNECT_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "support-banner",
    "title": "Need Help?",
    "visibility": "public",
    "status": "published",
    "content": "Having trouble? Reach out to our API support team at **api-support@bookstore.example.com** or join our [Slack community](https://bookstore-dev.slack.com)."
  }' | jq '{id, name, status}'
```

---

## Step 24 — Final Review

### Via Konnect UI — Complete Walkthrough

```
1. Dev Portal → bookstore-portal → Overview
   → Portal URL, developer count, application count

2. Dev Portal → bookstore-portal → Settings → Appearance
   → Dark theme with #8B4513 primary color

3. Dev Portal → bookstore-portal → Pages
   → 3 pages: Getting Started, Terms of Service, Changelog

4. Dev Portal → bookstore-portal → Snippets
   → support-banner snippet

5. API Products → Bookstore API
   → Version: v1.0.0 with OpenAPI spec
   → Implementation: linked to gateway service
   → Publication: published to bookstore-portal (public)
   → Documents: Quick Start Guide

6. Application Auth → bookstore-key-auth
   → Strategy type: key_auth, key name: apikey

7. Gateway Manager → your-control-plane → Services
   → Bookstore service with routes
   → CORS plugin (from decK) + konnect-application-auth plugin (auto-created)

8. Gateway Manager → your-control-plane → Plugins
   → konnect-application-auth (managed by Konnect, do not edit)
```

### Via API — Summary Script

```bash
echo "=== Portal ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID" | \
  jq '{name, default_domain, authentication_enabled, auto_approve_developers}'

echo -e "\n=== API Product ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID" | jq '{name, description}'

echo -e "\n=== Version ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/versions" | jq '.data[] | {name}'

echo -e "\n=== Publication ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID/publications" | \
  jq '.data[] | {visibility, auth_strategy_ids}'

echo -e "\n=== Pages ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/pages" | \
  jq '.data[] | {title, slug}'

echo -e "\n=== Developers ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/developers" | \
  jq '.data[] | {email, status}'

echo -e "\n=== Applications ==="
curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/applications" | \
  jq '.data[] | {name}'
```

Open the portal in a browser and verify:

- [ ] Dark theme with bookstore brown accent
- [ ] Getting Started, Terms of Service, Changelog pages visible
- [ ] Bookstore API in catalog with interactive OpenAPI docs
- [ ] "Quick Start" documentation tab on the API page
- [ ] "Try It" panel available
- [ ] Developer can register, create app, get key, call API

---

## Architecture Summary

```
Konnect Organization
│
├── Control Plane (your-control-plane)
│   ├── Service: bookstore (generated from OpenAPI via openapi2kong)
│   │   ├── Routes: /books, /books/{bookId}, /authors, /authors/{authorId}, /reviews
│   │   ├── Plugin: cors (for portal "Try It")
│   │   └── Plugin: konnect-application-auth (auto-created by auth strategy)
│   └── Credentials (managed by Konnect when developers register apps)
│
├── API Products
│   └── Bookstore API
│       ├── Version: v1.0.0 (OpenAPI spec)
│       ├── Implementation → bookstore service on CP
│       ├── Publication → bookstore-portal (public, key-auth)
│       └── Document: Quick Start Guide
│
├── Dev Portal (bookstore-portal)
│   ├── Customization (dark theme, #8B4513)
│   ├── Pages (Getting Started, Terms, Changelog)
│   ├── Snippets (support-banner)
│   └── Developers & Applications (self-service)
│
└── Auth Strategies
    └── bookstore-key-auth (key_auth → apikey header)
```

**The end-to-end flow:**

```
OpenAPI Spec
    │ deck file openapi2kong
    ▼
Kong Config (YAML)
    │ deck file add-plugins (CORS)
    ▼
Kong Config + CORS
    │ deck gateway sync
    ▼
Live Gateway Service
    │ Create API Product + Version + Implementation
    ▼
API Product in Catalog
    │ Publish to Portal + Attach Auth Strategy
    ▼
Developer Portal (live)
    │ Developer registers → creates app → gets API key
    ▼
Authenticated API Calls
    │ curl -H "apikey: KEY" → Kong → httpbin.org
    ▼
200 OK ✅ (or 401 without key ❌)
```

---

## Clean Up

> Run these steps to tear down everything and start fresh for a new bootcamp session.

### 1. Remove gateway config from the control plane

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force
```

### 2. Delete Konnect resources (via API)

```bash
# Delete portal pages
for PAGE_ID in $(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/pages" | jq -r '.data[].id'); do
  curl -s -X DELETE "$KONNECT_API/v3/portals/$PORTAL_ID/pages/$PAGE_ID" \
    -H "Authorization: Bearer $KONNECT_PAT"
  echo "Deleted page $PAGE_ID"
done

# Delete portal snippets
for SNIPPET_ID in $(curl -s -H "Authorization: Bearer $KONNECT_PAT" \
  "$KONNECT_API/v3/portals/$PORTAL_ID/snippets" | jq -r '.data[].id'); do
  curl -s -X DELETE "$KONNECT_API/v3/portals/$PORTAL_ID/snippets/$SNIPPET_ID" \
    -H "Authorization: Bearer $KONNECT_PAT"
  echo "Deleted snippet $SNIPPET_ID"
done

# Delete the portal
curl -s -X DELETE "$KONNECT_API/v3/portals/$PORTAL_ID" \
  -H "Authorization: Bearer $KONNECT_PAT"
echo "Deleted portal $PORTAL_ID"

# Delete the API product (also removes versions, publications, implementations)
curl -s -X DELETE "$KONNECT_API/v3/apis/$BOOKSTORE_API_ID" \
  -H "Authorization: Bearer $KONNECT_PAT"
echo "Deleted API product $BOOKSTORE_API_ID"

# Delete the auth strategy
curl -s -X DELETE "$KONNECT_API/v3/application-auth-strategies/$AUTH_STRATEGY_ID" \
  -H "Authorization: Bearer $KONNECT_PAT"
echo "Deleted auth strategy $AUTH_STRATEGY_ID"
```

### 3. Or delete via Konnect UI

```
1. Dev Portal → bookstore-portal → Settings → Delete Portal
2. API Products → Bookstore API → Settings → Delete
3. Application Auth → bookstore-key-auth → Delete
```

### 4. Clean generated files

```bash
# Remove files generated during the bootcamp (keeps source files intact)
rm -f deck/generated-kong.yaml deck/bookstore-final.yaml
```

After cleanup, only source files remain:

```
api-portal/
├── openapi/
│   └── bookstore-api.yaml       ← Source spec (kept)
├── deck/
│   └── plugin-cors.yaml          ← Plugin template (kept)
├── pages/                        ← Portal page content (kept)
├── docs/                         ← API docs (kept)
└── README.md                     ← This file (kept)
```

> **Ready for the next bootcamp:** Run Steps 1-13 to rebuild everything from scratch.

---

## Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `openapi2kong` produces empty output | Spec has no `servers` block | Add a `servers` entry with the upstream URL |
| API doesn't appear on portal | Missing publication | Publish the API product to the portal |
| "Try It" returns errors | Missing implementation | Link the API product to the gateway service |
| "Try It" says "Failed to fetch" | Proxy URL not set or not reachable | Set proxy URL on CP (Step 13b). If local DP, use ngrok or test via curl |
| Developer can't get credentials | No auth strategy on publication | Attach auth strategy to the publication |
| 401 with portal-issued key | Manual `key-auth` plugin conflicts with `konnect-application-auth` | Remove the manual `key-auth` plugin from decK config — Konnect manages auth via the portal auth strategy |
| 401 with portal-issued key | Auth strategy not attached to publication | Attach auth strategy in Step 12 |
| Portal shows but no APIs | API product exists but no publication | Create a publication |
| Upstream returns 404 (not 200) | The `deck file patch` step in Step 1 didn't run | Verify the service has `path: /anything` set (the patch step adds it); without it, `httpbin.org/books` returns 404 because httpbin doesn't have those paths |
| 404 from gateway | Routes not matching | Check route paths from `openapi2kong` output |

---

## Key Concepts

See the **"Concepts you'll meet in Part 2"** table near the top of this
file (immediately under the `# Part 2 —` heading) for the full glossary —
Product, Version, Spec, Implementation, Portal, Publication, Auth Strategy,
Application, Visibility, and `konnect-application-auth`.
