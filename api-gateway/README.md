# Kong API Gateway Bootcamp

> Choose your deployment guide based on your data plane setup.

## Deployment Options

| Guide | Style | When to use |
|---|---|---|
| [README-serverless.md](README-serverless.md) | decK CLI · Serverless DP | Quick demos, no Docker needed |
| [README-hybrid.md](README-hybrid.md) | decK CLI · Docker DP | Full control, HTTP Log, IP Restriction demos |
| [README-UI.md](README-UI.md) | Konnect UI walkthrough | Live demos / customer walkthroughs — click-by-click in Gateway Manager |

All three guides reach the **same end state**: 14 plugins on the same control plane. Pick one path or switch between them mid-bootcamp.

## What's Shared

```
api-gateway/
├── deck/                             ← 14 decK files (identical for both deployments)
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
│   └── 14-consumer-groups-acl.yaml
├── insomnia/
│   └── kong-gateway-bootcamp.json    ← Insomnia collection (has both environments)
├── README.md                         ← This file (index)
├── README-serverless.md              ← Konnect Serverless guide
└── README-hybrid.md                  ← Konnect + Docker Hybrid guide
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
