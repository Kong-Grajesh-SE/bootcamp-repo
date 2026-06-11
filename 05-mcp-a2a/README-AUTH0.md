# Auth0 Configuration for MCP OAuth2 (Step 5)

> Complete Auth0 tenant setup required before running Step 5 of the
> MCP & A2A bootcamp. Follow sections A–E in order, then verify with
> section F before proceeding to the Konnect UI or decK steps.

---

## A. Create an Auth0 Tenant

1. Go to [auth0.com](https://auth0.com) → **Sign Up** (free tier is sufficient)
2. Choose a tenant name and region:
   - **Tenant Name**: e.g. `bootcamp-mcp`
   - **Region**: `US`
3. Your tenant domain will be: `<tenant-name>.us.auth0.com`

```bash
export AUTH0_DOMAIN="<tenant-name>.us.auth0.com"
```

> If you already have an Auth0 tenant, skip to Section B.

---

## B. Create an API (Audience)

The API defines the `audience` claim that Auth0 stamps into every JWT.
Kong uses this to identify which tokens are intended for the MCP gateway.

1. **Auth0 Dashboard → Applications → APIs → + Create API**
2. Configure:

   | Field | Value |
   |---|---|
   | **Name** | `MCP Gateway API` |
   | **Identifier** | `https://mcp-gateway.bootcamp.dev` |
   | **Signing Algorithm** | `RS256` |

3. Click **Create**

> **Note:** The Identifier does not need to be a resolvable URL. It is a
> logical string used as the `aud` claim in the JWT. Auth0 never makes an
> HTTP request to it. You can use any unique string.

```bash
export AUTH0_API_AUDIENCE="https://mcp-gateway.bootcamp.dev"
```

---

## C. Create the Machine-to-Machine Application (Flow A)

This application is used for the `client_credentials` flow — server-to-server
authentication where the caller holds a client secret.

1. **Auth0 Dashboard → Applications → Applications → + Create Application**
2. Configure:

   | Field | Value |
   |---|---|
   | **Name** | `mcp-service-app` |
   | **Application Type** | `Machine to Machine Applications` |

3. Click **Create**
4. On the **Authorize** screen:
   - Select API: **MCP Gateway API**
   - Permissions: leave default (no specific scopes needed for the bootcamp)
   - Click **Authorize**
5. Go to the **Settings** tab and note:
   - **Client ID** → this is your `AUTH0_M2M_CLIENT_ID`
   - **Client Secret** → this is your `AUTH0_M2M_CLIENT_SECRET`

```bash
export AUTH0_M2M_CLIENT_ID="<paste Client ID from Settings>"
export AUTH0_M2M_CLIENT_SECRET="<paste Client Secret from Settings>"
```

---

## D. Create the Single Page Application (Flow B — PKCE)

This application is used for the `authorization_code + PKCE` flow — desktop
and CLI clients (VS Code, Claude Desktop) where no client secret can be
safely stored.

1. **Auth0 Dashboard → Applications → Applications → + Create Application**
2. Configure:

   | Field | Value |
   |---|---|
   | **Name** | `mcp-pkce-app` |
   | **Application Type** | `Single Page Application` |

3. Click **Create**
4. Go to the **Settings** tab and configure the following URLs
   (replace `$PROXY_URL` with your actual Konnect serverless proxy URL): https://95fa62461d.us.serverless.gateways.konggateway.com/mcp-oauth/callback

   | Field | Value |
   |---|---|
   | **Allowed Callback URLs** | `$PROXY_URL/mcp-oauth/callback` |
   | **Allowed Logout URLs** | `$PROXY_URL` |
   | **Allowed Web Origins** | `$PROXY_URL` |

   For example, if your proxy URL is `https://95fa62461d.us.serverless.gateways.konggateway.com`:

   | Field | Value |
   |---|---|
   | **Allowed Callback URLs** | `https://95fa62461d.us.serverless.gateways.konggateway.com/mcp-oauth/callback` |
   | **Allowed Logout URLs** | `https://95fa62461d.us.serverless.gateways.konggateway.com` |
   | **Allowed Web Origins** | `https://95fa62461d.us.serverless.gateways.konggateway.com` |

5. Scroll down → click **Save Changes**
6. Note the **Client ID** from the top of the Settings tab

```bash
export AUTH0_SPA_CLIENT_ID="zeaZmQdgTI3wVPOnkkhLC4bQKHIGdRhg"
```

> **PKCE is enabled by default** for Single Page Applications — there is no
> separate toggle to turn it on.

---

## E. Create a Test User (Optional — for PKCE browser login)

The PKCE flow (Flow B) requires a user to sign in via the browser. Create
a test user so you don't need a real account.

1. **Auth0 Dashboard → User Management → Users → + Create User**
2. Configure:

   | Field | Value |
   |---|---|
   | **Email** | `agent-user@bootcamp.dev` |
   | **Password** | `Agent123!` |
   | **Connection** | `Username-Password-Authentication` |

3. Click **Create**

---

## F. Verify Auth0 is Working

Run these three checks before proceeding to Step 5 in the bootcamp.

### F.1 — Get a token via client_credentials

```bash
curl -s -X POST https://$AUTH0_DOMAIN/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$AUTH0_M2M_CLIENT_ID" \
  -d "client_secret=$AUTH0_M2M_CLIENT_SECRET" \
  -d "audience=$AUTH0_API_AUDIENCE" \
  | jq '{token_type, expires_in, access_token: .access_token[:40]}'
```

**Expected:**
```json
{
  "token_type": "Bearer",
  "expires_in": 86400,
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6Ikp..."
}
```

### F.2 — Check the JWKS endpoint (what Kong uses to verify tokens)

```bash
curl -s https://$AUTH0_DOMAIN/.well-known/jwks.json | jq '.keys | length'
```

**Expected:** `1` or more (at least one RS256 signing key).

### F.3 — Check OpenID discovery (confirms issuer URL)

```bash
curl -s https://$AUTH0_DOMAIN/.well-known/openid-configuration \
  | jq '{issuer, jwks_uri, token_endpoint, authorization_endpoint}'
```

**Expected:**
```json
{
  "issuer": "https://<tenant-name>.us.auth0.com/",
  "jwks_uri": "https://<tenant-name>.us.auth0.com/.well-known/jwks.json",
  "token_endpoint": "https://<tenant-name>.us.auth0.com/oauth/token",
  "authorization_endpoint": "https://<tenant-name>.us.auth0.com/authorize"
}
```

---

## G. Summary of All Environment Variables

```bash
# Auth0 Tenant
export AUTH0_DOMAIN="<tenant-name>.us.auth0.com"

# API (audience)
export AUTH0_API_AUDIENCE="https://mcp-gateway.bootcamp.dev"

# Machine-to-Machine App (Flow A — client_credentials)
export AUTH0_M2M_CLIENT_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export AUTH0_M2M_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Single Page App (Flow B — PKCE)
export AUTH0_SPA_CLIENT_ID="yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
```

---

## H. How Auth0 Maps to the Kong Plugin

When you configure the `ai-mcp-oauth2` plugin in Step 5.3, the Auth0 values
map as follows:

| Kong Plugin Field | Auth0 Source |
|---|---|
| **Authorization Servers** | `https://$AUTH0_DOMAIN/` (the `issuer` from F.3) |
| **JWKS Endpoint** | `https://$AUTH0_DOMAIN/.well-known/jwks.json` (the `jwks_uri` from F.3) |
| **Resource** | `$PROXY_URL/mcp-oauth/tools` (your Kong route — not an Auth0 value) |
| **Insecure Relaxed Audience Validation** | `on` for the bootcamp (skips strict `aud` checking) |

The `audience` value (`AUTH0_API_AUDIENCE`) is used only when **requesting**
tokens — it must match the API Identifier from Section B so Auth0 issues
the token. Kong validates the JWT signature via JWKS, not the audience
(because `insecure_relaxed_audience_validation` is on for this demo).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `{"error": "access_denied"}` when requesting M2M token | Ensure `mcp-service-app` is authorized for `MCP Gateway API` (Section C, step 4) |
| `{"error": "unauthorized_client"}` on PKCE flow | Ensure `mcp-pkce-app` is a **Single Page Application**, not a Regular Web App |
| Callback URL mismatch error in browser | The URL in **Allowed Callback URLs** must exactly match `$PROXY_URL/mcp-oauth/callback` — no trailing slash, exact scheme |
| JWKS endpoint returns 404 | Check `AUTH0_DOMAIN` is correct — should be `<tenant>.us.auth0.com` (no `https://` prefix in the variable) |
| Token has no `aud` claim | You forgot to pass `audience` when requesting the token. Add `-d "audience=$AUTH0_API_AUDIENCE"` |
| Kong returns 401 with valid Auth0 token | Verify `Authorization Servers` in the plugin matches `https://$AUTH0_DOMAIN/` (trailing slash required) |

---

