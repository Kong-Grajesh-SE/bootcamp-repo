# Bring Your Own Agent - Exercise Prompts
#
# Copy-paste these prompts into your AI agent after installing kongctl skills.
# Each exercise builds on the previous one. The agent should use kongctl
# commands (explain, scaffold, plan, diff, apply) as instructed by the
# kongctl-declarative skill.
#
# Prerequisites:
#   1. kongctl install skills        (install skills into this repo)
#   2. kongctl login                 (authenticate with Konnect)
#   3. export CP_NAME="<your-cp>"   (set your control plane name)

# ─────────────────────────────────────────────────────────────────
# EXERCISE 1 - Discovery (read-only, safe)
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "What resources can I manage with kongctl? Run `kongctl explain apis`
#   and `kongctl explain portals` and summarize the key fields I need to
#   create an API and publish it on a developer portal."
#
# Expected agent actions:
#   - kongctl explain apis
#   - kongctl explain portals
#   - kongctl explain api_versions
#   - kongctl explain api_publications
#   - Summarizes required vs optional fields

# ─────────────────────────────────────────────────────────────────
# EXERCISE 2 - Scaffold and customize (generates files, no remote changes)
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "Scaffold a new Konnect API called 'Weather API' with description
#   'Real-time weather data for cities worldwide'. Save the YAML to
#   config/weather-api.yaml. Add a v1.0.0 version to it."
#
# Expected agent actions:
#   - kongctl scaffold apis --name weather-api
#   - Customizes the output YAML with description and version
#   - Writes config/weather-api.yaml

# ─────────────────────────────────────────────────────────────────
# EXERCISE 3 - Plan and apply (creates resources in Konnect)
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "Apply the Weather API config we just created. First show me the diff,
#   then apply it after I approve. Use `kongctl apply` (not sync)."
#
# Expected agent actions:
#   - kongctl diff --mode apply -f config/weather-api.yaml
#   - Waits for approval
#   - kongctl apply -f config/weather-api.yaml
#   - kongctl get apis (verify)

# ─────────────────────────────────────────────────────────────────
# EXERCISE 4 - Portal publication (end-to-end)
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "Create a developer portal called 'bootcamp-portal' and publish the
#   Weather API on it with public visibility. Put everything in a single
#   declarative YAML file. Preview the plan, then apply."
#
# Expected agent actions:
#   - Writes a YAML file with portal + api + publication using !ref
#   - kongctl plan --mode apply -f config/portal-publish.yaml --output-file plans/portal.json
#   - kongctl diff --plan plans/portal.json
#   - Waits for approval
#   - kongctl apply --plan plans/portal.json

# ─────────────────────────────────────────────────────────────────
# EXERCISE 5 - Namespace isolation (multi-team)
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "Set up namespace isolation: team-frontend owns the Weather API,
#   team-platform owns the portal. Show me how `kongctl sync` with
#   --require-namespace=team-frontend would only affect the frontend
#   team's resources."
#
# Expected agent actions:
#   - Updates YAML with kongctl.namespace on each resource
#   - kongctl diff --mode sync -f config/portal-publish.yaml --require-namespace=team-frontend
#   - Explains what gets affected vs protected

# ─────────────────────────────────────────────────────────────────
# EXERCISE 6 - Full stack with decK integration (advanced)
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "Create a complete setup: a developer portal, the Bookstore API with
#   an OpenAPI spec from openapi/bookstore-api.yaml, publish it on the
#   portal, and deploy it to my control plane using decK integration with
#   the existing services-and-routes.yaml. Show me the full plan."
#
# Expected agent actions:
#   - Writes full-stack YAML with portals, apis, _external CP, _deck
#   - kongctl plan --mode apply -f config/full-stack.yaml --output-file plans/full.json
#   - kongctl diff --plan plans/full.json
#   - Explains what kongctl manages vs what decK manages

# ─────────────────────────────────────────────────────────────────
# EXERCISE 7 - Clean up
# ─────────────────────────────────────────────────────────────────
#
# Prompt:
#
#   "Delete all the resources we created during these exercises.
#   Show me what will be deleted first."
#
# Expected agent actions:
#   - kongctl diff --mode delete -f config/portal-publish.yaml
#   - Waits for approval
#   - kongctl delete -f config/portal-publish.yaml --auto-approve
