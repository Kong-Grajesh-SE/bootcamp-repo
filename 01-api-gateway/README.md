# Kong API Gateway Bootcamp

> Choose your deployment guide based on your data plane setup.

## Deployment Options

| Guide | Style | When to use |
|---|---|---|
| [README-serverless.md](README-serverless.md) | decK CLI · Serverless DP | Quick demos, no Docker needed |
| [README-hybrid.md](README-hybrid.md) | decK CLI · Docker DP | Full control, HTTP Log, IP Restriction demos |
| [README-UI.md](README-UI.md) | Konnect UI walkthrough | Live demos / customer walkthroughs - click-by-click in Gateway Manager |

All three guides reach the **same end state**: 14 core plugins plus an
**Advanced Auth & Identity** track (steps 15–17) on the same control plane.
Pick one path or switch between them mid-bootcamp.

## Advanced Auth & Identity (steps 15–17)

Beyond the built-in `key-auth` and `jwt` plugins, the module adds federated
identity and OAuth demos:

| Step | What | Plugin | IdP |
|---|---|---|---|
| 15 | **Kong Identity** - Konnect-native machine-to-machine OAuth2 | `openid-connect` | [Kong Identity](https://developer.konghq.com/identity/) (Konnect-hosted) |
| 16 | OpenID Connect with **Keycloak** - bearer + browser SSO (alice/bob-admin), plus token introspection | `openid-connect` | Local Keycloak (Docker) |
| 17 | **Upstream OAuth** - Kong fetches an M2M token and injects it on the *upstream* call | [`upstream-oauth`](https://developer.konghq.com/plugins/upstream-oauth/) | Shared Keycloak (`kong-m2m`) |

Steps 16–17 use the **shared** bootcamp Keycloak at the repo root in
[../keycloak/](../keycloak/) (realm `bootcamp`) - start it with
`cd ../keycloak && docker compose up -d`.

## What's Shared

```
api-gateway/
├── deck/                             ← 17 decK files (identical for both deployments)
│   ├── 01-services-and-routes.yaml
│   ├── 02-rate-limiting.yaml
│   ├── 03-proxy-cache.yaml
│   ├── 04-upstream.yaml
│   ├── 05-key-auth.yaml
│   ├── 06-jwt-auth.yaml
│   ├── 07-consumers.yaml
│   ├── 08-cors.yaml
│   ├── 09-ip-restriction.yaml
│   ├── 10-correlation-id.yaml
│   ├── 11-request-transformer.yaml
│   ├── 12-response-transformer.yaml
│   ├── 13-http-log.yaml
│   ├── 14-consumer-groups-acl.yaml
│   ├── 15-kong-identity.yaml         ← Kong Identity (Konnect-native M2M)
│   ├── 16-oidc-keycloak.yaml         ← OpenID Connect via shared Keycloak
│   └── 17-upstream-oauth.yaml        ← Upstream OAuth (Kong → backend M2M token)
├── insomnia/
│   └── kong-gateway-bootcamp.json    ← Insomnia collection (has both environments)
├── README.md                         ← This file (index)
├── README-serverless.md              ← Konnect Serverless guide
├── README-hybrid.md                  ← Konnect + Docker Hybrid guide
└── README-UI.md                      ← Konnect UI walkthrough

# Keycloak for steps 16–17 is shared across modules - repo-root ../keycloak/ (realm `bootcamp`)
```

## Key Differences

| Feature | Serverless | Hybrid (Docker) |
|---------|-----------|-----------------|
| Setup time | 0 min (already running) | ~5 min (docker run) |
| Docker required | No | Yes |
| HTTP Log plugin | Needs public endpoint (webhook.site) | Works with `host.docker.internal:9999` |
| IP Restriction | Client IP = CDN edge IP | Client IP = Docker bridge (`172.x.x.x`) |
| httpbin.konghq.com | ⚠️ May be unreachable | ✅ Works (HTTP port 80) |
| HTTPS proxy | Built-in | `https://localhost:8443` (self-signed) |

## Quick Start (both deployments)

```bash
export KONNECT_TOKEN=<your-personal-access-token>
export CP_NAME="<your-control-plane-name>"

# Then follow the deployment-specific README for PROXY_URL and DP setup
```
