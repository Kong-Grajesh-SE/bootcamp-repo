# APIOps Bootcamp — Mastering decK Commands

> **Story:** You're the platform engineer for the **Bookstore API**.
> Every step uses the same `bookstore-service` so you can see how each decK command
> fits into a real API lifecycle — from first deployment through GitOps maturity.

---

## Prerequisites

- [decK CLI](https://docs.konghq.com/deck/latest/installation/) installed
- Konnect account with a control plane (or a local Kong Gateway)
- Terminal open in this `apiops/` directory

```bash
export KONNECT_TOKEN=kpat_FbER48Z5p8RLE0Q5aCecWcRb0nEAHneZzviSeHFLzltg29YN8
export CP_NAME=Grajesh-bootcamp
export PROXY_URL=http://localhost:8000
```

---

## File Structure

```
apiops/
├── deck/
│   ├── 01-bookstore-base.yaml        ← Base service + route (Step 1-4)
│   ├── 02-bookstore-plugins.yaml     ← + rate-limiting, correlation-id (Step 5-6)
│   ├── 03-bookstore-consumers.yaml   ← + key-auth, consumers (Step 7)
│   ├── 04-bookstore-tagged.yaml      ← Same service with tags (Step 15-17)
│   ├── 05-bookstore-templated.yaml   ← Same service with env var templates (Step 12)
│   ├── partial-services.yaml         ← Just the service (Step 11)
│   ├── partial-plugins.yaml          ← Just the plugins (Step 11)
│   ├── partial-consumers.yaml        ← Just the consumers (Step 11)
│   ├── plugin-cors.yaml              ← CORS plugin for add-plugins (Step 14)
│   └── patch-timeouts.json           ← JSONPath patch for timeouts (Step 13)
├── openapi/
│   └── bookstore-api.yaml            ← OpenAPI spec (Step 10)
├── lint/
│   └── ruleset.yaml                  ← Linting rules (Step 9)
└── README.md                         ← This file
```

---

## Command Reference

### Gateway Commands (Live Operations)

| Command | What It Does | Mutates Kong? | When to Use |
|---------|-------------|---------------|-------------|
| `deck gateway ping` | Tests connectivity | No | First step in any troubleshooting |
| `deck gateway dump` | Exports live state to YAML | No | Backup, audit, bootstrapping GitOps |
| `deck gateway diff` | Shows what would change | No | Before every sync, drift detection |
| `deck gateway sync` | Reconciles Kong to match YAML | **Yes** (deletes unmanaged entities) | Full-ownership deployments |
| `deck gateway apply` | Creates/updates, never deletes | No (additive only) | Shared environments, incremental changes |
| `deck gateway validate` | Checks YAML against live Kong | No | Pre-deployment validation |
| `deck gateway reset` | Deletes ALL entities | **Yes** (nuclear) | Clean slate, teardown |

### File Commands (Offline Operations)

| Command | What It Does | Needs Kong? | When to Use |
|---------|-------------|-------------|-------------|
| `deck file validate` | Schema and reference checks | No | CI pipeline, pre-commit |
| `deck file lint` | Custom governance rules | No | Enforce naming, tagging, standards |
| `deck file openapi2kong` | OpenAPI → Kong config | No | API-first workflows |
| `deck file merge` | Combine partial files | No | Multi-team, split configs |
| `deck file render` | Combine + resolve env vars + validate | No | Environment-specific builds |
| `deck file patch` | Modify values with JSONPath | No | Bulk updates, CI transforms |
| `deck file add-plugins` | Add plugins to config | No | Standardize plugin sets |
| `deck file add-tags` | Tag entities for scoping | No | Multi-team ownership |
| `deck file list-tags` | Show all tags in a file | No | Audit, discovery |
| `deck file remove-tags` | Remove tags from entities | No | Clean up, re-scope |

---

# Part 1 — Gateway Commands (Live Operations)

These commands talk to a **live Kong Gateway** (Konnect or self-managed).

---

## Step 1 — Test Connectivity (`deck gateway ping`)

> **What it does:** Verifies that decK can reach your Kong Gateway and authenticate.
> Use this as the first troubleshooting step when anything seems wrong.

```bash
deck gateway ping \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Expected output:**
```
Successfully Konnected to the Grajesh-Org organization!
```

**What to check if it fails:**

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Bad token | Regenerate PAT in Konnect → Personal Access Tokens |
| `control plane not found` | Wrong CP name | Check exact name in Gateway Manager |
| `connection refused` | Network issue | Check internet, VPN, proxy settings |

> **Teach:** This command does NOT read or write any config. It's purely a handshake.
> Always run `ping` before `diff` or `sync` to isolate auth issues from config issues.

---

## Step 2 — Validate YAML Before Deploying (`deck gateway validate`)

> **What it does:** Sends your YAML to Kong's validation API without applying it.
> Catches plugin config errors, invalid field values, and schema mismatches.

```bash
deck gateway validate deck/01-bookstore-base.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Expected output:**
```
(no output = valid)
```

Now try validating the file with plugins:

```bash
deck gateway validate deck/02-bookstore-plugins.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Try breaking it** — create a bad config to see the error:

```bash
# Create a temp file with an invalid plugin config
cat > /tmp/bad-config.yaml << 'EOF'
_format_version: "3.0"
services:
- name: bookstore-service
  url: https://httpbin.org
  routes:
  - name: bookstore-route
    paths:
    - /bookstore
  plugins:
  - name: rate-limiting
    config:
      minute: -1
      policy: invalid-policy
EOF

deck gateway validate /tmp/bad-config.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

> **Teach:** `gateway validate` checks against the **live Kong schema** — it knows which
> plugins are available, which fields are valid, and catches errors that `file validate`
> would miss. Use it in CI before `sync` to fail fast.

**Difference from `file validate`:**
- `deck file validate` → offline schema check (no Kong needed)
- `deck gateway validate` → checks against the live Kong version's schema (catches version-specific issues)

---

## Step 3 — Deploy the Bookstore (`deck gateway sync`)

> **What it does:** Makes Kong's live state **exactly match** your YAML file.
> Creates missing entities, updates changed ones, and **deletes entities not in the file**.
>
> ⚠️ This is the most powerful command — it's a full reconciliation.

```bash
deck gateway sync deck/01-bookstore-base.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Expected output:**
```
creating service bookstore-service
creating route bookstore-route
Summary:
  Created: 2
  Updated: 0
  Deleted: 0
```

**Verify it works:**

```bash
curl -s $PROXY_URL/bookstore/get | jq .url
# → "https://httpbin.org/get"

curl -s $PROXY_URL/bookstore/headers | jq .headers.Host
# → "httpbin.org"
```

> **Teach:** `sync` = "Kong should look exactly like this YAML, nothing more, nothing less."
> If you remove an entity from your YAML and re-sync, it gets **deleted** from Kong.
> This is GitOps-style: the repo is the single source of truth.

---

## Step 4 — Preview Changes Before Applying (`deck gateway diff`)

> **What it does:** Shows you what `sync` **would** do — without actually doing it.
> Think of it like `terraform plan` or `git diff`.

First, let's see what adding plugins would change:

```bash
deck gateway diff deck/02-bookstore-plugins.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Expected output:**
```
creating plugin rate-limiting for service bookstore-service
creating plugin correlation-id for service bookstore-service
creating plugin request-transformer for service bookstore-service
Summary:
  Created: 3
  Updated: 0
  Deleted: 0
```

**Nothing changed yet!** Kong still only has the base service. Let's verify:

```bash
curl -i $PROXY_URL/bookstore/get
# → No X-Request-ID header (correlation-id not applied yet)
```

> **Teach:** Always run `diff` before `sync` in production. It's your safety net.
> In CI/CD pipelines, `diff` runs on pull requests; `sync` runs on merge to main.

---

## Step 5 — Add Plugins Incrementally (`deck gateway apply`)

> **What it does:** Creates or updates entities from your YAML but **never deletes** anything.
> Safe for shared control planes where multiple teams own different entities.

```bash
deck gateway apply deck/02-bookstore-plugins.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Expected output:**
```
creating plugin rate-limiting for service bookstore-service
creating plugin correlation-id for service bookstore-service
creating plugin request-transformer for service bookstore-service
Summary:
  Created: 3
  Updated: 0
  Deleted: 0
```

**Verify the plugins are live:**

```bash
# Correlation ID added
curl -i $PROXY_URL/bookstore/get 2>&1 | grep -i x-request-id
# → X-Request-ID: uuid#1

# Request transformer added headers
curl -s $PROXY_URL/bookstore/headers | jq '.headers["X-Api-Version"]'
# → "v1"

curl -s $PROXY_URL/bookstore/headers | jq '.headers["X-Service"]'
# → "bookstore"

# Rate limiting active
curl -i $PROXY_URL/bookstore/get 2>&1 | grep -i x-ratelimit
# → X-RateLimit-Limit-Minute: 100
```

### `sync` vs `apply` — When to Use Which

| Scenario | Use | Why |
|----------|-----|-----|
| Single team owns the entire CP | `sync` | Full control, GitOps-clean |
| Multiple teams share a CP | `apply` | Won't delete another team's entities |
| CI/CD pipeline (main branch) | `sync` | Repo = source of truth |
| Quick plugin addition to prod | `apply` | Surgical, no side effects |
| Drift correction | `sync` | Forces CP back to desired state |

---

## Step 6 — Export Live State (`deck gateway dump`)

> **What it does:** Exports the current live Kong state to YAML.
> Use it to bootstrap GitOps from an existing Gateway, create backups, or audit drift.

```bash
# Dump to stdout
deck gateway dump \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

```bash
# Dump to a file
deck gateway dump -o output/live-state.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

```bash
# Dump in JSON format
deck gateway dump --format json \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Now compare live state against your file:**

```bash
# Dump live state, then diff your local file against it
deck gateway dump -o /tmp/live.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"

# Visual diff
diff deck/02-bookstore-plugins.yaml /tmp/live.yaml
```

> **Teach:** `dump` is read-only — it never changes anything.
> Common uses:
> - **Bootstrap GitOps:** dump a manually configured Gateway into YAML, commit it, manage with `sync` going forward
> - **Backup:** dump before risky changes
> - **Audit:** compare live state against repo to detect unauthorized changes

---

## Step 7 — Full Config with Consumers (`deck gateway sync` — round 2)

> **What it does:** Syncs the consumers file, which adds key-auth + consumers.
> This shows how `sync` handles the progression from plugins to consumers.

First, preview what will change:

```bash
deck gateway diff deck/03-bookstore-consumers.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

Notice: the diff shows the correlation-id and request-transformer plugins from Step 5
will be **deleted** because they're not in `03-bookstore-consumers.yaml`. That's `sync`
being honest — it reconciles to exactly what's in the file.

```bash
deck gateway sync deck/03-bookstore-consumers.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

**Verify:**

```bash
# No key → 401
curl -i $PROXY_URL/bookstore/get

# Admin key → 200
curl -i $PROXY_URL/bookstore/get -H "apikey: admin-key-abc123"
# → X-Consumer-Username: bookstore-admin

# Reader key → 200
curl -i $PROXY_URL/bookstore/get -H "apikey: reader-key-def456"
# → X-Consumer-Username: bookstore-reader
```

> **Teach:** This is a key `sync` lesson — it **deleted** the plugins from Step 5
> that weren't in the consumers file. In real GitOps, you maintain **one complete
> file** (or use `merge` to combine partials) so nothing gets accidentally removed.

---

## Step 8 — Nuclear Reset (`deck gateway reset`)

> **What it does:** Deletes **every entity** in the control plane.
> This is the nuclear option — use it for teardown or to start completely fresh.
>
> ⚠️ **Destructive.** Requires `--force` flag. No undo.

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force
```

**Verify everything is gone:**

```bash
curl -s $PROXY_URL/bookstore/get
# → {"message":"no Route matched with those values"}

deck gateway dump \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
# → _format_version: "3.0" (empty — no entities)
```

> **Teach:** `reset` is rarely used in production. It's for:
> - Tearing down a demo or test control plane
> - Starting over after a botched migration
> - Cleaning up before a fresh `sync` in CI
>
> In real workflows, prefer `sync` with an empty base file over `reset`.

---

# Part 2 — File Commands (Offline Operations)

These commands work **without a live Kong Gateway**. They transform, validate,
and manipulate YAML files locally — perfect for CI pipelines and GitOps workflows.

---

## Step 9 — Schema Validation (`deck file validate`)

> **What it does:** Checks YAML structure and schema offline — no Kong connection needed.
> Catches syntax errors, missing required fields, and malformed configs.

```bash
# Validate the base file
deck file validate deck/01-bookstore-base.yaml
```

```bash
# Validate the consumers file
deck file validate deck/03-bookstore-consumers.yaml
```

**Try breaking it:**

```bash
cat > /tmp/broken.yaml << 'EOF'
_format_version: "3.0"
services:
- name: bookstore-service
  url: https://httpbin.org
  invalid_field: true
  routes:
  - name: bookstore-route
    paths: not-a-list
EOF

deck file validate /tmp/broken.yaml
```

> **Teach:** `file validate` is fast and offline — use it in pre-commit hooks and CI.
> It catches structural errors but can't validate plugin-specific configs (that's `gateway validate`).

### `file validate` vs `gateway validate`

| Check | `file validate` | `gateway validate` |
|-------|----------------|-------------------|
| YAML syntax | ✅ | ✅ |
| Schema structure | ✅ | ✅ |
| Plugin config values | ❌ | ✅ |
| Plugin availability | ❌ | ✅ |
| Version-specific fields | ❌ | ✅ |
| Needs Kong? | No | Yes |
| Speed | Fast | Slower (network) |

---

## Step 10 — Lint Against Rules (`deck file lint`)

> **What it does:** Runs custom governance rules against your YAML.
> Enforce naming conventions, required tags, timeout policies — whatever your team decides.

```bash
# Lint the base file (no tags → will fail!)
deck file lint \
  -s deck/01-bookstore-base.yaml \
  lint/ruleset.yaml
```

**Expected:** Errors about missing tags (the base file has no tags).

```bash
# Lint the tagged file (has tags → should pass)
deck file lint \
  -s deck/04-bookstore-tagged.yaml \
  lint/ruleset.yaml
```

**Expected:** Clean pass (all entities have tags, names are kebab-case).

**Review the ruleset:**

```bash
cat lint/ruleset.yaml
```

The ruleset enforces:
- ❌ `no-untagged-services` — every service must have tags
- ⚠️ `no-untagged-routes` — routes should have tags
- ❌ `service-name-convention` — kebab-case names only
- ❌ `route-name-convention` — kebab-case names only
- ⚠️ `service-timeouts` — explicit timeout config recommended
- ⚠️ `service-retries` — explicit retry config recommended

> **Teach:** Linting is how platform teams enforce standards at scale.
> Put `deck file lint` in your CI pipeline to block PRs that don't follow conventions.
> Write rules for what matters to your org: naming, tagging, timeout policies, etc.

---

## Step 11 — OpenAPI → Kong Config (`deck file openapi2kong`)

> **What it does:** Generates Kong Gateway config (services, routes) from an OpenAPI spec.
> This is the **API-first** workflow — start with a spec, auto-generate the gateway config.

```bash
deck file openapi2kong \
  --spec openapi/bookstore-api.yaml \
  --output-file output/from-openapi.yaml
```

**Inspect the generated config:**

```bash
cat output/from-openapi.yaml
```

You'll see Kong services and routes auto-generated from the OpenAPI paths:
- `/books` → route with GET, POST
- `/books/{bookId}` → route with GET, PUT, DELETE
- `/authors` → route with GET
- `/authors/{authorId}` → route with GET
- `/reviews` → route with GET, POST

The upstream URL comes from the `servers` block in the OpenAPI spec.

**Validate the generated config:**

```bash
deck file validate output/from-openapi.yaml
```

> **Teach:** API-first means the OpenAPI spec is the source of truth.
> Developers define the API contract, `openapi2kong` generates the gateway layer.
> You can then layer on plugins, consumers, and policies with `merge` or `add-plugins`.

---

## Step 12 — Combine Partial Files (`deck file merge`)

> **What it does:** Merges multiple partial YAML files into one complete config.
> This is how teams split ownership — one file per concern, combined at deploy time.

```bash
deck file merge \
  deck/partial-services.yaml \
  deck/partial-plugins.yaml \
  deck/partial-consumers.yaml \
  --output-file output/merged.yaml
```

**Inspect the result:**

```bash
cat output/merged.yaml
```

You'll see all three files combined:
- `bookstore-service` with its route (from partial-services)
- `rate-limiting`, `key-auth`, `correlation-id` plugins (from partial-plugins)
- `bookstore-admin`, `bookstore-reader`, `bookstore-guest` consumers (from partial-consumers)

**Validate the merged output:**

```bash
deck file validate output/merged.yaml
```

**You can even sync the merged output directly:**

```bash
# Preview first
deck gateway diff output/merged.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME"
```

> **Teach:** Merge enables a split-by-concern file layout:
> - `services.yaml` — owned by the platform team
> - `plugins.yaml` — owned by the security team
> - `consumers.yaml` — owned by the API consumers team
>
> Each team manages their file independently. CI merges them before `sync`.

---

## Step 13 — Resolve Environment Variables (`deck file render`)

> **What it does:** Takes a templated YAML file with `${{ env "VAR" }}` placeholders,
> resolves them against your shell environment, and outputs a concrete YAML file.
> Use `--populate-env-vars` to substitute real values; without it, deck mocks them.

```bash
# First, look at the template
cat deck/05-bookstore-templated.yaml
# → You'll see ${{ env "DECK_UPSTREAM_URL" }}, ${{ env "DECK_ENV" }}, etc.
```

```bash
# Render for dev (set env vars, then render)
DECK_ENV=dev \
DECK_UPSTREAM_URL=https://httpbin.org \
DECK_RATE_LIMIT=60 \
DECK_CONNECT_TIMEOUT=30000 \
DECK_READ_TIMEOUT=30000 \
DECK_WRITE_TIMEOUT=30000 \
deck file render deck/05-bookstore-templated.yaml \
  --populate-env-vars \
  --output-file output/rendered-dev.yaml

cat output/rendered-dev.yaml
# → url: https://httpbin.org, minute: 60, env:dev
```

```bash
# Render for staging (different values)
DECK_ENV=staging \
DECK_UPSTREAM_URL=https://httpbun.com \
DECK_RATE_LIMIT=200 \
DECK_CONNECT_TIMEOUT=60000 \
DECK_READ_TIMEOUT=60000 \
DECK_WRITE_TIMEOUT=60000 \
deck file render deck/05-bookstore-templated.yaml \
  --populate-env-vars \
  --output-file output/rendered-staging.yaml

cat output/rendered-staging.yaml
# → url: https://httpbun.com, minute: 200, env:staging
```

**Compare dev vs staging:**

```bash
diff output/rendered-dev.yaml output/rendered-staging.yaml
```

> **Teach:** Templating lets you use **one YAML file** across all environments.
> The template lives in the repo; environment-specific values come from CI variables,
> Vault, or deployment configs. No more copying files per environment.
>
> Without `--populate-env-vars`, deck substitutes mock placeholder values — useful
> for previewing structure without real config.

---

## Step 14 — Patch Values (`deck file patch`)

> **What it does:** Modifies specific values in a YAML file using JSONPath selectors.
> Great for bulk updates without editing YAML by hand.

```bash
# Look at the patch file
cat deck/patch-timeouts.json
```

The patch changes all services to:
- `retries: 5` (was 3)
- `connect_timeout: 60000` (was 30000)
- `read_timeout: 60000` (was 30000)
- `write_timeout: 60000` (was 30000)

```bash
# Apply the patch to the base file (inline selector + value)
deck file patch \
  -s deck/01-bookstore-base.yaml \
  --selector '$..services[*]' \
  --value 'retries:5' \
  --output-file output/patched.yaml
```

**Or use a patch file with multiple operations:**

```bash
deck file patch \
  -s deck/01-bookstore-base.yaml \
  deck/patch-timeouts.json \
  --output-file output/patched.yaml
```

**Compare before and after:**

```bash
diff deck/01-bookstore-base.yaml output/patched.yaml
# → retries: 3 → 5, timeouts: 30000 → 60000
```

> **Teach:** Patches are powerful for CI workflows:
> - Bump all timeouts before deploying to a slow environment
> - Override URLs for a canary deployment
> - Apply org-wide policy changes across many files

---

## Step 15 — Add Plugins to Config (`deck file add-plugins`)

> **What it does:** Adds plugin configurations to an existing YAML file.
> Use it to layer standard plugins onto any config without manual YAML editing.

```bash
# Add a CORS plugin to the base config
deck file add-plugins \
  -s deck/01-bookstore-base.yaml \
  deck/plugin-cors.yaml \
  --output-file output/with-cors.yaml
```

**Inspect the result:**

```bash
cat output/with-cors.yaml
# → bookstore-service now has a CORS plugin attached
```

**Chain it — add plugins to the OpenAPI-generated config:**

```bash
# Generate from OpenAPI, then add standard plugins
deck file openapi2kong --spec openapi/bookstore-api.yaml \
  --output-file /tmp/from-spec.yaml

deck file add-plugins \
  -s /tmp/from-spec.yaml \
  deck/plugin-cors.yaml \
  --output-file output/spec-with-plugins.yaml
```

> **Teach:** `add-plugins` is the bridge between API-first and platform standards.
> API teams define specs; the platform team adds security, observability, and traffic
> plugins automatically in CI — no manual YAML editing needed.

---

## Step 16 — Tag Entities (`deck file add-tags`)

> **What it does:** Adds tags to all entities in a YAML file.
> Tags are how decK scopes ownership — `select_tags` lets each team sync only their entities.

```bash
# Add team and environment tags to the base file
deck file add-tags \
  --selector '$.services[*]' \
  --value 'team:bookstore' \
  deck/01-bookstore-base.yaml \
  --output-file output/tagged.yaml
```

**Or add tags to everything:**

```bash
deck file add-tags \
  deck/01-bookstore-base.yaml \
  team:bookstore env:production \
  --output-file output/tagged-all.yaml
```

**Verify tags were added:**

```bash
deck file list-tags output/tagged-all.yaml
```

> **Teach:** Tags enable multi-team ownership of a shared control plane:
> ```bash
> # Team A syncs only their entities
> deck gateway sync team-a-config.yaml --select-tag team:payments
>
> # Team B syncs only their entities
> deck gateway sync team-b-config.yaml --select-tag team:orders
> ```
> Without tags, `sync` would delete the other team's entities.

---

## Step 17 — List Tags (`deck file list-tags`)

> **What it does:** Shows all tags used in a YAML file. Useful for auditing and discovery.

```bash
# List tags in the tagged file
deck file list-tags deck/04-bookstore-tagged.yaml
```

**Expected output:**
```
team:bookstore
env:staging
```

```bash
# List tags in the consumers file (no tags → empty)
deck file list-tags deck/03-bookstore-consumers.yaml
```

> **Teach:** Use `list-tags` to audit tag coverage before enabling `select_tags` scoping.
> If entities are missing tags, they'll be invisible to scoped syncs — and could get
> deleted by another team's `sync`.

---

## Step 18 — Remove Tags (`deck file remove-tags`)

> **What it does:** Removes specific tags from entities. Use when re-scoping ownership.

```bash
# Remove the staging tag
deck file remove-tags \
  deck/04-bookstore-tagged.yaml \
  env:staging \
  --output-file output/untagged.yaml
```

**Verify:**

```bash
deck file list-tags output/untagged.yaml
# → team:bookstore (env:staging is gone)
```

```bash
# Remove ALL tags
deck file remove-tags \
  deck/04-bookstore-tagged.yaml \
  team:bookstore env:staging \
  --output-file output/no-tags.yaml

deck file list-tags output/no-tags.yaml
# → (empty)
```

> **Teach:** Tag lifecycle matters:
> - Migrating a service from team A to team B? Remove old tags, add new ones.
> - Promoting from staging to production? Swap `env:staging` for `env:production`.

---

# Part 3 — Putting It All Together: A GitOps Pipeline

Here's how these commands chain together in a real CI/CD pipeline:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Git Push / PR                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  deck file validate  │  ← Syntax & schema check
                    │  deck file lint      │  ← Naming, tags, standards
                    └──────────┬──────────┘
                               │ pass
                    ┌──────────▼──────────┐
                    │  deck file merge     │  ← Combine team files
                    │  deck file render    │  ← Resolve env vars
                    │  deck file add-tags  │  ← Add deployment tags
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ deck gateway validate│  ← Check against live Kong
                    └──────────┬──────────┘
                               │ pass
              ┌────────────────┼────────────────┐
              │ PR (preview)   │                 │ Merge (deploy)
    ┌─────────▼─────────┐           ┌───────────▼──────────┐
    │  deck gateway diff │           │  deck gateway sync    │
    │  (show changes)    │           │  (apply changes)      │
    └────────────────────┘           └───────────┬──────────┘
                                                 │
                                      ┌──────────▼──────────┐
                                      │  deck gateway diff   │  ← Verify: no drift
                                      │  (expect zero diff)  │
                                      └─────────────────────┘
```

### Example CI Script

```bash
#!/bin/bash
set -euo pipefail

# 1. Validate offline
deck file validate deck/*.yaml
for f in deck/*.yaml; do deck file lint -s "$f" lint/ruleset.yaml; done

# 2. Build deployment artifact
deck file merge deck/partial-*.yaml --output-file /tmp/merged.yaml
deck file render /tmp/merged.yaml --populate-env-vars --output-file /tmp/rendered.yaml
deck file add-tags /tmp/rendered.yaml team:bookstore env:$ENVIRONMENT \
  --output-file /tmp/final.yaml

# 3. Validate against live Kong
deck gateway ping --konnect-token $KONNECT_TOKEN --konnect-control-plane-name $CP_NAME
deck gateway validate /tmp/final.yaml \
  --konnect-token $KONNECT_TOKEN --konnect-control-plane-name $CP_NAME

# 4. Deploy (or preview)
if [ "$CI_BRANCH" = "main" ]; then
  deck gateway sync /tmp/final.yaml \
    --konnect-token $KONNECT_TOKEN --konnect-control-plane-name $CP_NAME
  
  # 5. Verify zero drift
  deck gateway diff /tmp/final.yaml \
    --konnect-token $KONNECT_TOKEN --konnect-control-plane-name $CP_NAME
else
  deck gateway diff /tmp/final.yaml \
    --konnect-token $KONNECT_TOKEN --konnect-control-plane-name $CP_NAME
fi
```

---

## Clean Up

```bash
# Reset Kong to empty
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name "$CP_NAME" \
  --force

# Clean generated output files
rm -f output/*

# Clean temp files created during the bootcamp
rm -f /tmp/bad-config.yaml \
      /tmp/broken.yaml \
      /tmp/live.yaml \
      /tmp/from-spec.yaml \
      /tmp/merged.yaml \
      /tmp/rendered.yaml \
      /tmp/final.yaml
```

**What gets cleaned:**

| Source | Files | Created In |
|--------|-------|-----------|
| `output/` | `live-state.yaml`, `from-openapi.yaml`, `merged.yaml`, `rendered-dev.yaml`, `rendered-staging.yaml`, `patched.yaml`, `with-cors.yaml`, `spec-with-plugins.yaml`, `tagged.yaml`, `tagged-all.yaml`, `untagged.yaml`, `no-tags.yaml` | Steps 6, 11-18 |
| `/tmp/` | `bad-config.yaml`, `broken.yaml`, `live.yaml`, `from-spec.yaml`, `merged.yaml`, `rendered.yaml`, `final.yaml` | Steps 2, 6, 9, 15, CI script |

---

## Quick Reference Card

```
GATEWAY (live):   ping → validate → diff → sync/apply → dump → reset
FILE (offline):   validate → lint → openapi2kong → merge → render → patch → add-plugins → add/list/remove-tags
```

| Want to... | Run |
|-----------|-----|
| Check if decK can reach Kong | `deck gateway ping` |
| See what would change | `deck gateway diff <file>` |
| Deploy (full ownership) | `deck gateway sync <file>` |
| Deploy (shared CP, additive) | `deck gateway apply <file>` |
| Backup live state | `deck gateway dump -o backup.yaml` |
| Check YAML syntax (offline) | `deck file validate <file>` |
| Enforce standards | `deck file lint -s <file> rules.yaml` |
| Generate from OpenAPI | `deck file openapi2kong --spec spec.yaml -o out.yaml` |
| Combine team files | `deck file merge a.yaml b.yaml -o combined.yaml` |
| Resolve env vars | `deck file render template.yaml --populate-env-vars -o resolved.yaml` |
| Bulk-update values | `deck file patch -s <file> patch.json -o out.yaml` |
| Add standard plugins | `deck file add-plugins -s <file> plugins.yaml -o out.yaml` |
| Tag for scoping | `deck file add-tags <file> team:X env:Y -o out.yaml` |
| Audit tags | `deck file list-tags <file>` |
| Remove tags | `deck file remove-tags <file> env:old -o out.yaml` |
| Delete everything | `deck gateway reset --force` |
