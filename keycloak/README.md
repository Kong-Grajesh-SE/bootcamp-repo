# Shared Keycloak - Bootcamp OIDC / OAuth2 provider

A single Keycloak instance with one realm (`bootcamp`) used by every module that
needs an external identity provider. Start it once and leave it running across
modules.

## Start / stop

```bash
cd keycloak
docker compose up -d          # first start imports realm-bootcamp.json
docker compose down -v        # stop and wipe
```

- Admin Console: http://localhost:8080 - `admin` / `admin`
- Realm: `bootcamp`
- Issuer from your **host** (curl/browser): `http://localhost:8080/realms/bootcamp`
- Issuer from **inside a container** (Kong DP): `http://host.docker.internal:8080/realms/bootcamp`

Verify:

```bash
curl -s http://localhost:8080/realms/bootcamp/.well-known/openid-configuration | jq .issuer
# → "http://localhost:8080/realms/bootcamp"
```

## Users (shared across modules)

| Username | Password | Realm role | Group | Used by |
|---|---|---|---|---|
| `alice` | `alice-password` | `user` | `travel-users` | 01 (OIDC) |
| `bob-admin` | `bob-password` | `admin` | `platform-engineers` | 01 (OIDC) |
| `agent-user` | `agent123` | `user` | - | 05 (MCP) |

## Clients (one per use case - kept distinct per module)

| Client | Type | Grants | Secret | Module |
|---|---|---|---|---|
| `kong` | confidential | auth code · password · client_credentials | `kong-bootcamp-client-secret-replace-in-prod` | 01 |
| `kong-m2m` | confidential | client_credentials | `kong-m2m-client-secret-replace-in-prod` | 01 |
| `mcp-service-client` | confidential | client_credentials | `mcp-service-secret` | 05 |
| `mcp-pkce-client` | public | auth code + PKCE | _(none)_ | 05 |

> ⚠️ These secrets are committed for bootcamp convenience only. **Never** use
> them in production - generate real secrets and store them in a vault.

## ⚠️ Issuer & host resolution (read before module 01 step 16)

Keycloak has **two names** for the same server:

| Caller | Reaches Keycloak at |
|---|---|
| Your host (curl, browser) | `localhost:8080` |
| Inside a container (Kong DP) | `host.docker.internal:8080` |

OpenID Connect validates that a token's `iss` claim equals the issuer the plugin
uses. Because the Kong DP container can **only** reach Keycloak at
`host.docker.internal:8080`, that's its issuer - so any token it accepts must
also carry `iss = http://host.docker.internal:8080/realms/bootcamp`. Keycloak
stamps `iss` from the host used to *request* the token, so you must mint tokens
against the same host.

The simplest robust setup is to use `host.docker.internal:8080` as the **single
issuer everywhere** and make your host resolve it (one-time):

```bash
echo "127.0.0.1 host.docker.internal" | sudo tee -a /etc/hosts
```

Docker Desktop already resolves `host.docker.internal` inside containers; this
adds it on the host too. On **native Linux**, also start the Kong DP with
`--add-host=host.docker.internal:host-gateway`.

- **Module 01 (`openid-connect`)** is discovery-driven (one issuer for both keys
  and `iss` validation) → it needs the hostname trick above.
- **Module 05 (`ai-mcp-oauth2`)** sets `jwks_endpoint` separately from
  `authorization_servers`, so it validates the signature via
  `host.docker.internal` while keeping `iss = localhost` → **no `/etc/hosts`
  change needed there.**
- **Serverless DPs** avoid the whole issue: the issuer is a single public ngrok
  URL that both the cloud DP and your host hit.

## Notes

- **Only one Keycloak runs** for the whole bootcamp; it binds host port `8080`.
  The per-module `keycloak/` folders were removed in favour of this shared one.
- **Serverless data planes** can't reach `localhost:8080`. Expose Keycloak with
  `ngrok http 8080`, set its `frontendUrl` to the ngrok URL so the token `iss`
  claim matches, and use that HTTPS URL as the issuer. The realm pre-approves
  `https://*.kongcloud.dev/*` and
  `https://*.us.serverless.gateways.konggateway.com/*` as redirect URIs.
