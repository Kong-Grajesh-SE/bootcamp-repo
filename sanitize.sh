#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# sanitize.sh - Reset all sensitive values back to safe placeholders
# ─────────────────────────────────────────────────────────────────────────────
# Run this BEFORE committing to ensure no real tokens, secrets, or
# environment-specific URLs leak into git.
#
# Usage:
#   ./sanitize.sh          # Dry-run: show what would change
#   ./sanitize.sh --apply  # Actually perform the replacements
#
# The script is idempotent - running it multiple times is safe.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")"

DRY_RUN=true
if [[ "${1:-}" == "--apply" ]]; then
  DRY_RUN=false
fi

CHANGED=0

# ─────────────────────────────────────────────────────────────────────────────
# Helper: replace a literal string in files matching a glob
# ─────────────────────────────────────────────────────────────────────────────
replace_literal() {
  local find="$1"
  local replace="$2"
  shift 2
  local files=("$@")

  for file in "${files[@]}"; do
    [[ -f "$file" ]] || continue
    if grep -qF "$find" "$file" 2>/dev/null; then
      CHANGED=$((CHANGED + 1))
      if $DRY_RUN; then
        echo "  [DRY-RUN] $file"
        echo "    - $find"
        echo "    + $replace"
      else
        # Use perl with env vars to avoid shell escaping issues
        FIND_STR="$find" REPLACE_STR="$replace" perl -pi -e '
          s/\Q$ENV{FIND_STR}\E/$ENV{REPLACE_STR}/g
        ' "$file"
        echo "  [FIXED] $file"
      fi
    fi
  done
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: replace a regex pattern in files matching a glob
# ─────────────────────────────────────────────────────────────────────────────
replace_regex() {
  local pattern="$1"
  local replace="$2"
  shift 2
  local files=("$@")

  for file in "${files[@]}"; do
    [[ -f "$file" ]] || continue
    if grep -qE "$pattern" "$file" 2>/dev/null; then
      CHANGED=$((CHANGED + 1))
      if $DRY_RUN; then
        echo "  [DRY-RUN] $file (regex: $pattern)"
      else
        sed -i '' -E "s|${pattern}|${replace}|g" "$file"
        echo "  [FIXED] $file"
      fi
    fi
  done
}

# ─────────────────────────────────────────────────────────────────────────────
# Collect target files
# ─────────────────────────────────────────────────────────────────────────────
READMES=($(find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/.git/*"))
DECK_YAMLS=($(find . -path "*/deck/*.yaml" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/output/*"))
ALL_TARGETS=("${READMES[@]}" "${DECK_YAMLS[@]}")

echo "═══════════════════════════════════════════════════════════════════"
echo " Bootcamp Sanitizer — Replacing sensitive values with placeholders"
echo "═══════════════════════════════════════════════════════════════════"
if $DRY_RUN; then
  echo " Mode: DRY-RUN (pass --apply to actually write changes)"
else
  echo " Mode: APPLYING changes"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Konnect Personal Access Tokens (kpat_*)
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ Konnect Tokens (kpat_*)"

# Known tokens — add yours here if you use different ones
replace_literal "kpat_5OZWjf2yXGtnA8yjgDBP1ykaBJgUHVEPtU8RYIBDURkufLjHA" "<your-konnect-pat>" "${ALL_TARGETS[@]}"
replace_literal "kpat_FbER48Z5p8RLE0Q5aCecWcRb0nEAHneZzviSeHFLzltg29YN8" "<your-konnect-pat>" "${ALL_TARGETS[@]}"
replace_literal "kpat_oJtQgNdPE1a2eEv1TZOyXrKr8ojSMmA6uMmnBA7gb6SWPec6B" "<your-konnect-pat>" "${ALL_TARGETS[@]}"
replace_literal "kpat_1VoffHZeCSq6FYQvMTJyJBEYYna826t58fZkovKIuZlwYjj9X" "<your-konnect-pat>" "${ALL_TARGETS[@]}"

# Catch-all: any kpat_ token not already a placeholder
replace_regex 'kpat_[A-Za-z0-9_-]{20,}' '<your-konnect-pat>' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 2. Serverless Proxy URLs
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ Serverless Proxy URLs"

replace_literal "https://6d62edef09.us.serverless.gateways.konggateway.com" 'https://<YOUR_SERVERLESS_PROXY_URL>' "${ALL_TARGETS[@]}"
replace_literal "https://6784e03d14.us.serverless.gateways.konggateway.com" 'https://<YOUR_SERVERLESS_PROXY_URL>' "${ALL_TARGETS[@]}"
replace_literal "https://95fa62461d.us.serverless.gateways.konggateway.com" 'https://<YOUR_SERVERLESS_PROXY_URL>' "${ALL_TARGETS[@]}"

# Catch-all: any serverless proxy URL pattern
replace_regex 'https://[a-f0-9]{10,}\.us\.serverless\.gateways\.konggateway\.com' 'https://<YOUR_SERVERLESS_PROXY_URL>' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 3. Control Plane Names
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ Control Plane Names"

replace_literal 'CP_NAME="This-Bootcamp"' 'CP_NAME="<your-control-plane-name>"' "${ALL_TARGETS[@]}"
replace_literal "CP_NAME=\"enablement-repo-gateway\"" 'CP_NAME="<your-control-plane-name>"' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 4. Control Plane Admin API URLs (with UUIDs)
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ Admin API URLs"

replace_literal "https://us.api.konghq.com/v2/control-planes/bb92c1d4-81e1-41ac-8971-d19d56cf79fe" 'https://us.api.konghq.com/v2/control-planes/<your-control-plane-id>' "${ALL_TARGETS[@]}"
replace_literal "https://us.api.konghq.com/v2/control-planes/62944782-1d63-4bcb-870c-8a513546251a" 'https://us.api.konghq.com/v2/control-planes/<your-control-plane-id>' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 5. Auth0 Credentials
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ Auth0 Credentials"

# Auth0 domain
replace_literal "dev-rf5ek3gg4bkog2ah.us.auth0.com" '<AUTH0_DOMAIN>' "${ALL_TARGETS[@]}"

# Auth0 client ID (Regular Web App)
replace_literal "oUYTyMdQx8hLfRzXe5BUXdLfL9DBwpoQ" '<AUTH0_CLIENT_ID>' "${ALL_TARGETS[@]}"

# Auth0 client secret (Regular Web App)
replace_literal "wY6VTR7TK4XFe4RloYPkLQrlC6moPo3Um6r4xOYecyhv6kCULdTcxXEzRNColx03" '<AUTH0_CLIENT_SECRET>' "${ALL_TARGETS[@]}"

# Auth0 SPA Client ID (MCP module)
replace_literal "zeaZmQdgTI3wVPOnkkhLC4bQKHIGdRhg" '<AUTH0_SPA_CLIENT_ID>' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 6. Kong Identity Credentials
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ Kong Identity Credentials"

replace_literal "https://zmk2nw5s1h5udfmg.us.identity.konghq.com/auth" 'https://<KONG_IDENTITY_ISSUER_URL>' "${ALL_TARGETS[@]}"
replace_literal "gsjbeyco72vgip1w" '<KONG_IDENTITY_CLIENT_ID>' "${ALL_TARGETS[@]}"
replace_literal "dt8iarwf8q61g3jbtj1lbaas" '<KONG_IDENTITY_CLIENT_SECRET>' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 7. JWT Secrets
# ─────────────────────────────────────────────────────────────────────────────
echo "▸ JWT Secrets"

replace_literal "9905688994c4a2ae380fc2e21c50df417b9c125ab760dd235b24af0bd191a628" '<REPLACE-WITH-RANDOM-SECRET>' "${ALL_TARGETS[@]}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════"
if [[ $CHANGED -eq 0 ]]; then
  echo " ✓ All files are already clean — nothing to sanitize."
else
  if $DRY_RUN; then
    echo " Found $CHANGED file(s) with sensitive values."
    echo " Run './sanitize.sh --apply' to fix them."
  else
    echo " ✓ Sanitized $CHANGED file(s). Safe to commit."
  fi
fi
echo "═══════════════════════════════════════════════════════════════════"
