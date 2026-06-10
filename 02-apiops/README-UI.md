# APIOps Bootcamp - Konnect UI Walkthrough

> The UI companion to the CLI-driven apiops bootcamp. Several decK commands
> (`patch`, `render`, `lint`, `merge`, `add-plugins`, `add-tags`) have **no Konnect
> UI equivalent** because they're CI-time transformations on YAML files. This
> guide covers the gateway-side operations (Sync, Dump, Reset) and shows you the
> UI screens that mirror the decK state - so you can verify by eye after each
> CLI step. If you want a pure-UI bootcamp, see `api-gateway/README-UI.md`.

> **Story:** You're the platform engineer for the **Bookstore API**. The CLI
> walkthrough deploys this same service through `deck gateway sync`. Here we
> rebuild it click-by-click, then point at the UI controls that correspond to
> each decK gateway verb (`ping`, `dump`, `sync`/`apply`, `reset`).

---

## Prerequisites

1. **Konnect account** at [cloud.konghq.com](https://cloud.konghq.com)
2. **Control Plane** named `<your-control-plane>` with at least one connected Data Plane
3. **Proxy URL** - typically `http://localhost:8000` or your DP ingress

```bash
export PROXY_URL=http://localhost:8000
```

> **What this UI walkthrough does NOT replace:** the offline `deck file *`
> toolchain. Lint rules, JSONPath patches, OpenAPI-to-Kong transforms with
> templating - those are designed to run in your CI pipeline against YAML on
> disk. The Konnect UI is the *runtime* surface; decK file commands are the
> *build* surface. The "UI-skip" section at the bottom explains why each
> offline command is still worth keeping in CI.

---

## Scope Map - CLI Step ↔ UI Equivalent

| CLI Step (apiops/README.md) | decK Command | UI Equivalent |
|---|---|---|
| Step 1 - Test connectivity | `deck gateway ping` | Gateway Manager → Control Plane shows **Connected** badge |
| Step 2 - Validate YAML | `deck gateway validate` | No direct UI (form validation on Save is the closest) |
| Step 3 - Deploy base service | `deck gateway sync` | Services → New Service + New Route |
| Step 4 - Preview changes | `deck gateway diff` | No direct UI (manual entity-count compare) |
| Step 5 - Add plugins | `deck gateway apply` | Plugins → New Plugin |
| Step 6 - Export live state | `deck gateway dump` | Control Plane → **Export Configuration** |
| Step 7 - Add consumers + key-auth | `deck gateway sync` | Consumers → New Consumer + credentials |
| Step 8 - Nuclear reset | `deck gateway reset` | Manually delete entities, or use Import Configuration with empty YAML |
| Step 11 - OpenAPI → Kong | `deck file openapi2kong` | **Import OpenAPI Spec** (Gateway Manager only generates the service/routes) |
| Step 16 - Tag entities | `deck file add-tags` | Service → Edit → **Tags** field |

---

# Part 1 - Gateway Operations with UI Equivalents

## Step 1 - Verify Connectivity (UI ↔ `deck gateway ping`)

The CLI walkthrough opens with a handshake:

```bash
deck gateway ping \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name $CP_NAME
```

The UI version is purely visual:

1. Sign in to [cloud.konghq.com](https://cloud.konghq.com)
2. Go to **Gateway Manager**
3. Click into `<your-control-plane>`
4. Look at the **Data Plane Nodes** section (or the top-right CP status indicator)

**Expected:** At least one node shows a green **Connected** badge with a recent
heartbeat timestamp.

**What this tells you:**

| UI Signal | Equivalent CLI Output |
|---|---|
| Green "Connected" badge | `Successfully Konnected to the <org> organization!` |
| No nodes listed | `connection refused` - DP not running |
| "Awaiting Ingest" | DP started but no telemetry yet - wait 30s |
| 403 on the CP page | Wrong org or token scope (`401 Unauthorized` in CLI) |

> **Why this matters:** Like `ping`, this view doesn't mutate anything. Use it
> as your first triage step before clicking Save on any entity.

---

## Step 2 - Note on Validation (UI ↔ `deck gateway validate`)

There is no first-class "Validate Without Applying" button in the Konnect UI.
The closest equivalents:

- **Form-level validation:** When you fill out a plugin or service form and
  click **Save**, the UI sends a `PATCH`/`POST` to the Admin API. If the
  payload is invalid, the form turns red and highlights the offending field.
- **Import Configuration dry-run:** When you upload a YAML file (see Step 6.2),
  Konnect parses it server-side and reports schema errors before applying.

The CLI command sends YAML to Kong's validation endpoint without applying:

```bash
deck gateway validate deck/02-bookstore-plugins.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name $CP_NAME
```

> **Why use the CLI for this anyway:** CI pipelines need machine-readable
> exit codes. The UI's red form fields don't fail a pull request.

---

## Step 3 - Deploy the Bookstore Service (UI ↔ `deck gateway sync` round 1)

This is the UI version of syncing `deck/01-bookstore-base.yaml`.

### 3.1 Create the Service

1. Go to **Gateway Manager → `<your-control-plane>` → Gateway Services**
2. Click **New Gateway Service**
3. Configure:
   - **Name**: `bookstore-service`
   - **Upstream URL**: `https://httpbin.org`
   - **Retries**: `3`
   - **Connect Timeout**: `30000`
   - **Read Timeout**: `30000`
   - **Write Timeout**: `30000`
4. Click **Save**

### 3.2 Create the Route

1. On the `bookstore-service` detail page, go to the **Routes** tab
2. Click **New Route**
3. Configure:
   - **Name**: `bookstore-route`
   - **Path(s)**: `/bookstore`
   - **Protocols**: `http`, `https`
   - **Strip Path**: `on`
4. Click **Save**

### 3.3 Test the Service

```bash
curl -s $PROXY_URL/bookstore/get | jq .url
# → "https://httpbin.org/get"

curl -s $PROXY_URL/bookstore/headers | jq .headers.Host
# → "httpbin.org"
```

**Expected:** httpbin echoes the request back, proxied through Kong.

> **Why this matters:** A `sync` is a *full reconciliation* - anything not in
> the YAML gets deleted. Clicking through the UI is *additive* by default; the
> UI counterpart of sync's destructive behavior is **Import Configuration**
> (Step 6.2) or manual deletion.

---

## Step 5 - Add Plugins to the Service (UI ↔ `deck gateway apply`)

This is the UI version of applying `deck/02-bookstore-plugins.yaml`.

### 5.1 Add Rate Limiting

1. Navigate to `bookstore-service` → **Plugins** tab
2. Click **New Plugin**
3. Search for `Rate Limiting` (the **classic** one, not RLA)
4. Configure:
   - **Minute**: `100`
   - **Policy**: `local`
5. Click **Save**

### 5.2 Add Correlation ID

1. On the service Plugins tab, click **New Plugin**
2. Search for `Correlation ID`
3. Configure:
   - **Header Name**: `X-Request-ID`
   - **Generator**: `uuid#counter`
   - **Echo Downstream**: `on`
4. Click **Save**

### 5.3 Add Request Transformer

1. On the service Plugins tab, click **New Plugin**
2. Search for `Request Transformer`
3. Configure **Add → Headers** (add each as a separate entry):
   - `X-API-Version:v1`
   - `X-Service:bookstore`
4. Click **Save**

### 5.4 Test

```bash
# Correlation-ID flowing through
curl -i $PROXY_URL/bookstore/get 2>&1 | grep -i x-request-id
# → X-Request-ID: <uuid>

# Request transformer headers reaching upstream
curl -s $PROXY_URL/bookstore/headers | jq '.headers["X-Api-Version"]'
# → "v1"

curl -s $PROXY_URL/bookstore/headers | jq '.headers["X-Service"]'
# → "bookstore"

# Rate limit headers present
curl -i $PROXY_URL/bookstore/get 2>&1 | grep -i x-ratelimit
# → X-RateLimit-Limit-Minute: 100
```

> **Why this matters:** Clicking Save in the UI is `deck gateway apply` —
> additive only. The UI never deletes plugins you didn't touch. That's why
> the CLI's `sync` workflow needs the YAML to be *complete* every run.

---

## Step 6 - Export Live State (UI ↔ `deck gateway dump`)

CLI:

```bash
deck gateway dump -o output/live-state.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name $CP_NAME
```

UI version:

### 6.1 Export Configuration

1. Go to **Gateway Manager → `<your-control-plane>`**
2. Click the **Actions** menu (top-right of the CP page)
3. Click **Export Configuration**
4. Choose format: **YAML** (or JSON - mirrors `--format json`)
5. Click **Download**

You'll get a file containing every service, route, plugin, and consumer
currently in the control plane - the same shape as `deck gateway dump`
output, ready to commit to git.

**Verify it matches the CLI dump:**

```bash
# Compare your UI download against a fresh CLI dump
deck gateway dump -o /tmp/cli-dump.yaml \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name $CP_NAME

diff ~/Downloads/<your-control-plane>-config.yaml /tmp/cli-dump.yaml
```

> **Why this matters:** `dump` (and Export Configuration) is **read-only**.
> Use it to:
> - Bootstrap GitOps from a manually configured CP
> - Take a backup before risky changes
> - Audit drift between what's in git and what's actually running

### 6.2 Import Configuration (UI ↔ `deck gateway sync` from a file)

Konnect can also accept the inverse - upload a YAML and have it become the live
state. This is the UI counterpart of `deck gateway sync`.

1. Go to **Gateway Manager → `<your-control-plane>`**
2. Click **Actions → Import Configuration**
3. Upload a decK-format YAML file (e.g., the file you just exported)
4. Review the preview pane - Konnect shows entities to be **created**, **updated**, or **deleted**
5. Click **Apply**

This preview pane is the closest UI analogue to `deck gateway diff`. The Apply
button is the closest UI analogue to `deck gateway sync` - including the
destructive part where unmanaged entities get removed.

> **Why use the CLI version:** Import Configuration is interactive. CI/CD
> needs a non-interactive workflow that exits with a useful code, which is
> what `deck gateway sync` provides.

---

## Step 7 - Add Consumers and Key-Auth (UI ↔ `deck gateway sync` round 2)

This is the UI version of `deck/03-bookstore-consumers.yaml`.

> **Important pre-step:** The CLI `sync` of the consumers file *deletes* the
> correlation-id and request-transformer plugins from Step 5 (they're not in
> the consumers file). The UI version does NOT do this automatically - if you
> want to mirror the CLI exactly, delete those two plugins manually first.

### 7.1 Update the Rate-Limiting Plugin

The consumers file changes the rate-limiting policy:

1. Navigate to `bookstore-service` → **Plugins** tab
2. Click the existing **Rate Limiting** plugin → **Edit**
3. Change **Minute**: `60` (was `100`)
4. Click **Save**

### 7.2 Add Key-Auth Plugin

1. On the Plugins tab, click **New Plugin**
2. Search for `Key Authentication`
3. Configure:
   - **Key Names**: `apikey`
   - **Hide Credentials**: `on`
4. Click **Save**

### 7.3 Create the Admin Consumer

1. Go to **Gateway Manager → `<your-control-plane>` → Consumers**
2. Click **New Consumer**
3. Configure:
   - **Username**: `bookstore-admin`
   - **Custom ID**: `admin-001`
4. Click **Save**
5. On the consumer detail page, go to **Credentials → Key Authentication**
6. Click **New Key Authentication Credential**
7. Set **Key**: `admin-key-abc123`
8. Click **Save**

### 7.4 Create the Reader Consumer

1. Back to **Consumers → New Consumer**
2. Configure:
   - **Username**: `bookstore-reader`
   - **Custom ID**: `reader-002`
3. Click **Save**
4. On the consumer detail page → **Credentials → Key Authentication**
5. Click **New Key Authentication Credential**
6. Set **Key**: `reader-key-def456`
7. Click **Save**

### 7.5 Test

```bash
# No key → 401
curl -i $PROXY_URL/bookstore/get
# → HTTP/1.1 401 Unauthorized

# Admin key → 200
curl -i $PROXY_URL/bookstore/get -H "apikey: admin-key-abc123" 2>&1 | grep -i x-consumer-username
# → X-Consumer-Username: bookstore-admin

# Reader key → 200
curl -i $PROXY_URL/bookstore/get -H "apikey: reader-key-def456" 2>&1 | grep -i x-consumer-username
# → X-Consumer-Username: bookstore-reader
```

> **Why this matters:** `sync` deletes entities not in the file; the UI does
> not. In real GitOps, you maintain *one complete file* (or use `deck file
> merge` to combine partials in CI) so this destructive behavior is intended,
> not accidental.

---

## Step 8 - Tag Entities (UI ↔ `deck file add-tags` for live entities)

`deck file add-tags` works on YAML files. The UI counterpart edits live
entities directly.

### 8.1 Tag the Service

1. Go to **Gateway Manager → `<your-control-plane>` → Gateway Services**
2. Click `bookstore-service` → **Edit**
3. Scroll to the **Tags** field
4. Add tags (one per entry):
   - `team:bookstore`
   - `env:staging`
5. Click **Save**

### 8.2 Tag the Route

1. From the service page, click into `bookstore-route` → **Edit**
2. Add tags:
   - `team:bookstore`
   - `env:staging`
3. Click **Save**

### 8.3 Tag the Plugin

1. From the service page, **Plugins** tab
2. Click the `rate-limiting` plugin → **Edit**
3. Add tags:
   - `team:bookstore`
   - `env:staging`
4. Click **Save**

### 8.4 Verify

Re-export the configuration (Step 6.1) and confirm the YAML now shows tags on
every entity - matching what `deck/04-bookstore-tagged.yaml` looks like on
disk.

> **Why this matters:** Tags drive `select_tags` scoping in CLI workflows.
> If you plan to share `<your-control-plane>` across teams, every entity
> needs a tag - otherwise it'll be invisible to scoped syncs and could get
> deleted by another team's full `sync`.

---

## Step 9 - Import OpenAPI Spec (UI ↔ `deck file openapi2kong`)

The CLI command converts an OpenAPI spec into Kong YAML offline:

```bash
deck file openapi2kong \
  --spec openapi/bookstore-api.yaml \
  --output-file output/from-openapi.yaml
```

Konnect has an equivalent under Service Catalog / API Specs (the exact menu
location moves between releases; current path is **Gateway Manager → Service
Catalog → Specs** or via the API product flow):

### 9.1 Upload the Spec

1. Go to **Gateway Manager → `<your-control-plane>` → Specs** (or the API
   product → **Versions → Add Spec**)
2. Click **Upload Spec** or **Import OpenAPI**
3. Select `apiops/openapi/bookstore-api.yaml`
4. Konnect parses the spec and offers to **Generate Gateway Configuration**
5. Review the proposed services/routes:
   - `/books` → GET, POST
   - `/books/{bookId}` → GET, PUT, DELETE
   - `/authors` → GET
   - `/authors/{authorId}` → GET
   - `/reviews` → GET, POST
6. Click **Create**

**The upstream URL** comes from the `servers` block in the OpenAPI spec
(`https://httpbin.org`).

> **Why use the CLI version:** `openapi2kong` runs offline and writes a YAML
> file you can commit to git. The UI version creates live entities directly —
> great for prototyping, but it skips the "review in PR" step that decK enables.

---

## Step 10 - Reset the Control Plane (UI ↔ `deck gateway reset`)

CLI:

```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name $CP_NAME \
  --force
```

There is **no single "Reset Everything" button** in the UI. Three workarounds:

### 10.1 Manual Cascade Delete

1. Go to **Gateway Manager → `<your-control-plane>` → Gateway Services**
2. Click `bookstore-service` → **Delete**
3. Confirm - the route and route-scoped plugins cascade
4. Go to **Consumers** → delete each consumer
5. Go to **Plugins** (global) → delete any remaining ones

### 10.2 Import an Empty Config (closer to `reset` in spirit)

1. Create an empty decK file:
   ```bash
   cat > /tmp/empty.yaml <<'EOF'
   _format_version: "3.0"
   EOF
   ```
2. **Gateway Manager → `<your-control-plane>` → Actions → Import Configuration**
3. Upload `/tmp/empty.yaml`
4. The preview shows everything to be **deleted**
5. Click **Apply**

This is the closest UI analogue to a full reset - it forces the live state to
match the empty YAML, deleting every entity.

### 10.3 Verify

```bash
curl -s $PROXY_URL/bookstore/get
# → {"message":"no Route matched with those values"}
```

Refresh the UI - Services, Routes, Plugins, and Consumers tabs should all be empty.

> **Why use the CLI version:** `deck gateway reset --force` is one command
> in a teardown script. The UI version is interactive and easy to get wrong.

---

# Part 2 - Commands With No UI Equivalent (the "UI-skip" list)

These decK commands operate on YAML files and have no counterpart in the
Konnect UI. They live in your CI pipeline, not in the browser. Each is worth
keeping even if you do most of your work in the UI:

| decK Command | What It Does | Why You Still Want It in CI |
|---|---|---|
| `deck file validate` | Offline schema/syntax check on YAML | Catches typos in PRs before they reach Konnect - fast, no network |
| `deck file lint -s <file> ruleset.yaml` | Custom governance rules (naming, tags, timeouts) | The UI can't enforce "every service must have tags" - only your linter can block the PR |
| `deck file render --populate-env-vars` | Substitutes `${{ env "VAR" }}` placeholders | One templated YAML, many environments - the UI has no concept of templates |
| `deck file merge a.yaml b.yaml` | Combines partial team-owned files | Lets multiple teams each own a YAML file; CI merges them - the UI is a single shared canvas |
| `deck file patch -s <file> patch.json` | JSONPath bulk updates (e.g., bump every timeout) | "Set retries to 5 on every service" is one command; the UI would take 50 clicks |
| `deck file add-plugins -s <file> plugin.yaml` | Layers standard plugins onto any config | The platform team auto-attaches CORS/observability plugins in CI - no manual UI edits per API |
| `deck file add-tags <file> team:X env:Y` | Adds tags to every entity in a file | UI tagging is per-entity click-through; `add-tags` does the whole file at once |
| `deck file list-tags <file>` | Audits tag coverage in a YAML file | UI has no "show me all tags used" view - useful before enabling `select_tags` scoping |
| `deck file remove-tags <file> env:old` | Bulk-strips tags from entities | Promotion from staging → prod swaps tags; bulk is faster than per-entity edits |
| `deck gateway validate <file>` | Validates YAML against live Kong schema | Returns a non-zero exit on bad config - wires cleanly into PR checks; the UI's red form fields don't fail CI |
| `deck gateway diff <file>` | Preview what `sync` would do | Import Configuration shows a preview, but the CLI version is scriptable and PR-attachable |

### A note on `templates with env vars`

`deck/05-bookstore-templated.yaml` uses `${{ env "DECK_UPSTREAM_URL" }}` and
similar placeholders. The Konnect UI has no equivalent - you'd need to
maintain one set of UI configurations per environment (dev, staging, prod) and
keep them in sync by hand. The templating + `render` workflow exists precisely
to avoid that drift.

---

# Part 3 - When to Click vs. When to Commit

| Situation | Use the UI | Use decK CLI |
|---|---|---|
| One-off prototype on a dev CP | Yes | Optional |
| Production deploy | No | Yes (CI runs `sync`) |
| First-time CP bootstrap | Yes (export afterward) | Run `dump` to capture state |
| Multi-team shared CP | Read-only | Yes (`select_tags` scoping) |
| Enforce naming conventions | No | Yes (`deck file lint`) |
| Promote staging → prod | No | Yes (`render` with different env vars) |
| Inspect what's running | Yes | `dump` for a snapshot |
| Rollback after a bad sync | Import a prior `dump` | Re-`sync` the previous YAML |

---

## Cleanup

Either approach works:

**UI:**
1. **Gateway Manager → `<your-control-plane>` → Actions → Import Configuration**
2. Upload an empty file (`_format_version: "3.0"` only)
3. Confirm the preview shows everything being deleted
4. Click **Apply**

**CLI:**
```bash
deck gateway reset \
  --konnect-token $KONNECT_TOKEN \
  --konnect-control-plane-name $CP_NAME \
  --force
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Data Plane shows "Disconnected" | Restart the DP container; check `KONG_CLUSTER_CONTROL_PLANE` env var |
| Save button greyed out on plugin form | A required field is empty or invalid - scroll for red highlights |
| Export Configuration produces empty YAML | The CP has no entities, or your role lacks read scope on this CP |
| Import Configuration preview shows surprise deletions | Your uploaded YAML is incomplete - use `deck file merge` to combine partials before upload |
| Consumer's key-auth credential not accepted | Verify the `apikey` header name matches the Key Authentication plugin's **Key Names** field |
| Tags missing from exported YAML | Tags must be added per-entity; bulk tagging requires `deck file add-tags` in CI |
| OpenAPI Import doesn't show all paths | Konnect ignores paths that lack `operationId` - add one per operation in the spec |

---

## Quick Reference

```
GATEWAY OPS WITH UI:    Connect badge → Services/Routes/Plugins forms → Export → Import → manual delete
GATEWAY OPS CLI-ONLY:   validate, diff (in CI, with exit codes)
FILE OPS CLI-ONLY:      validate, lint, render, merge, patch, add-plugins, add/list/remove-tags
```

| Want to... | UI Path | CLI Equivalent |
|---|---|---|
| Verify CP is reachable | Gateway Manager → CP → **Connected** badge | `deck gateway ping` |
| Deploy a service | Services → New Gateway Service | `deck gateway sync` |
| Add a plugin | Service → Plugins → New Plugin | `deck gateway apply` |
| Export live state | Actions → **Export Configuration** | `deck gateway dump` |
| Upload a YAML config | Actions → **Import Configuration** | `deck gateway sync` |
| Tag an entity | Edit → **Tags** field | `deck file add-tags` (bulk) |
| Generate from OpenAPI | Specs → **Import OpenAPI** | `deck file openapi2kong` |
| Wipe everything | Import empty YAML, or delete manually | `deck gateway reset --force` |
| Enforce naming/tag rules | (no UI) | `deck file lint` |
| Render env-specific YAML | (no UI) | `deck file render --populate-env-vars` |
| Combine team-owned partials | (no UI) | `deck file merge` |
| Bulk-update field values | (no UI) | `deck file patch` |
