#!/usr/bin/env bash
# Switch the OpenClaw model — primary AND fallback — from either provider:
#   • OU AI Sandbox (LiteLLM gateway) — needs LITELLM_API_KEY
#   • OpenRouter — needs OPENROUTER_API_KEY
# Both catalogs are polled up front. You only see providers you hold a key
# for; with no keys at all the script explains and exits. Prices are shown
# per million tokens (input/output) in the menus and after selection.
# The gateway hot-reloads (no restart).
set -uo pipefail
# Make 'openclaw' findable in non-interactive shells.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_env.sh" 2>/dev/null || true

LITELLM_BASE_URL="${LITELLM_BASE_URL:-https://litellm.lib.ou.edu}"
ENV_FILE="${HOME}/.openclaw/.env"
oubase="${LITELLM_BASE_URL%/}"
TTY="${SELECT_MODEL_TTY:-/dev/tty}"   # overridable for testing
TOP_N="${SELECT_MODEL_TOP_N:-20}"

read_env() { # read_env VAR -> value from process env or ~/.openclaw/.env
  local var="$1" val="${!1:-}"
  [[ -z "${val}" && -f "${ENV_FILE}" ]] && val="$(grep -E "^${var}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  printf '%s' "${val}"
}

# ---- prerequisites --------------------------------------------------------
need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ Required tool '$1' not found — $2"; exit 1; }; }
need curl    "rebuild the Codespace or install curl."
need python3 "rebuild the Codespace or install python3."
need openclaw "OpenClaw isn't on PATH yet — start the Gateway task first, or run: bash .devcontainer/setup.sh"

# ---- key detection --------------------------------------------------------
OU_KEY="$(read_env LITELLM_API_KEY)"
[[ "${OU_KEY}" == "sk-REPLACE_ME" ]] && OU_KEY=""
OR_KEY="$(read_env OPENROUTER_API_KEY)"

if [[ -z "${OU_KEY}" && -z "${OR_KEY}" ]]; then
  echo "❌ No API keys found — nothing to select a model from."
  echo "   • OU AI Sandbox key:  run  bash scripts/set-key.sh  (LITELLM_API_KEY, starts with sk-)"
  echo "   • OpenRouter key:     add the OPENROUTER_API_KEY Codespaces secret (starts with sk-or-)"
  echo "   Add at least one, then re-run this script."
  exit 1
fi

# ---- poll OU catalog (if key) ---------------------------------------------
# MODELS/PRICES file format (tab-separated): ref \t display-line
# ref is the full OpenClaw model ref, e.g. litellm/Qwen3 Coder 30B
OU_ROWS_FILE=/tmp/select_model_ou_rows.tsv; : > "${OU_ROWS_FILE}"
if [[ -n "${OU_KEY}" ]]; then
  echo "Polling OU AI Sandbox catalog (${oubase}) ..."
  http=000
  for url in "${oubase}/v1/models" "${oubase}/models"; do
    http="$(curl -s -m 20 -o /tmp/ou_models.json -w '%{http_code}' -H "Authorization: Bearer ${OU_KEY}" "${url}" || echo 000)"
    [[ "${http}" == "200" ]] && break
  done
  case "${http}" in
    200) ;;
    401|403) echo "❌ OU key rejected (HTTP ${http}). Fix it with: bash scripts/set-key.sh"; [[ -z "${OR_KEY}" ]] && exit 1; echo "   Continuing with OpenRouter only."; OU_KEY="" ;;
    000)     echo "❌ Could not reach ${oubase}."; [[ -z "${OR_KEY}" ]] && exit 1; echo "   Continuing with OpenRouter only."; OU_KEY="" ;;
    *)       echo "❌ OU gateway returned HTTP ${http}."; [[ -z "${OR_KEY}" ]] && exit 1; echo "   Continuing with OpenRouter only."; OU_KEY="" ;;
  esac
fi
if [[ -n "${OU_KEY}" ]]; then
  # Pricing (best effort): LiteLLM /model/info exposes per-token costs when
  # the gateway is configured with them; otherwise we show "price n/a".
  curl -s -m 20 -H "Authorization: Bearer ${OU_KEY}" "${oubase}/model/info" -o /tmp/ou_model_info.json \
    || curl -s -m 20 -H "Authorization: Bearer ${OU_KEY}" "${oubase}/v1/model/info" -o /tmp/ou_model_info.json \
    || : > /tmp/ou_model_info.json
  python3 - > "${OU_ROWS_FILE}" <<'PY'
import json
def load(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return {}
models = sorted({m.get("id","") for m in load("/tmp/ou_models.json").get("data",[]) if m.get("id")})
prices = {}
for e in load("/tmp/ou_model_info.json").get("data",[]) or []:
    name = e.get("model_name") or ""
    info = e.get("model_info") or {}
    ci, co = info.get("input_cost_per_token"), info.get("output_cost_per_token")
    try:
        if ci is not None and co is not None:
            prices[name] = (float(ci)*1e6, float(co)*1e6)
    except Exception:
        pass
for mid in models:
    p = prices.get(mid)
    if p and (p[0] or p[1]): price = f"${p[0]:.2f}/${p[1]:.2f} /M"
    elif p:                  price = "FREE"
    else:                    price = "price n/a"
    print(f"litellm/{mid}\t{price:<18} {mid}")
PY
  [[ -s "${OU_ROWS_FILE}" ]] || { echo "❌ No models parsed from the OU response."; [[ -z "${OR_KEY}" ]] && exit 1; echo "   Continuing with OpenRouter only."; OU_KEY=""; }
fi

# ---- poll OpenRouter catalog + weekly rankings (if key) --------------------
OR_ROWS_FILE=/tmp/select_model_or_rows.tsv; : > "${OR_ROWS_FILE}"
OR_CATALOG=/tmp/or_models.json
if [[ -n "${OR_KEY}" ]]; then
  kc="$(curl -s -m 15 -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${OR_KEY}" https://openrouter.ai/api/v1/key || echo 000)"
  if [[ "${kc}" != "200" ]]; then
    echo "⚠️  OpenRouter key check returned HTTP ${kc} — it may be invalid, expired, or out of credit."
    echo "    Models will still be listed, but calls will fail at runtime until the key works."
  fi
  echo "Polling OpenRouter catalog + weekly popularity rankings ..."
  if ! curl -fsS -m 30 "https://openrouter.ai/api/v1/models" -o "${OR_CATALOG}"; then
    echo "❌ Could not reach OpenRouter (network/endpoint)."
    [[ -z "${OU_KEY}" ]] && exit 1
    echo "   Continuing with OU Sandbox only."; OR_KEY=""
  else
    # Rankings are best-effort (undocumented endpoint); on failure we fall
    # back to tool-capable models from major vendors sorted free-then-cheapest.
    curl -fsS -m 30 "https://openrouter.ai/api/frontend/models/find?order=top-weekly" -o /tmp/or_rankings.json || : > /tmp/or_rankings.json
    python3 - "${TOP_N}" > "${OR_ROWS_FILE}" <<'PY'
import json, sys
TOP_N = int(sys.argv[1])
def load(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return {}
catalog = {m.get("id"): m for m in load("/tmp/or_models.json").get("data",[]) if m.get("id")}
def tool_capable(m): return "tools" in (m.get("supported_parameters") or [])
def perM(v):
    try: return float(v)*1e6
    except Exception: return None
def fmt(m):
    pr = m.get("pricing") or {}
    pin, pout = perM(pr.get("prompt")), perM(pr.get("completion"))
    ctx = m.get("context_length") or 0
    ctxs = f"{ctx//1000}k" if ctx else "?"
    if pin == 0 and pout == 0: price = "FREE"
    elif pin is not None and pout is not None: price = f"${pin:.2f}/${pout:.2f} /M"
    else: price = "price n/a"
    return f"{price:<18} {m['id']} ({ctxs})"
ranked = []
d = load("/tmp/or_rankings.json").get("data") or {}
for m in (d.get("models") or []):
    slug = m.get("slug")
    if slug and slug in catalog and tool_capable(catalog[slug]):
        ranked.append(slug)
    if len(ranked) >= TOP_N: break
if not ranked:  # rankings unavailable → curated fallback
    popular = {"anthropic","openai","google","x-ai","meta-llama","mistralai",
               "qwen","deepseek","z-ai","moonshotai","minimax"}
    rows = []
    for mid, m in catalog.items():
        vendor = mid.split("/")[0]
        if vendor not in popular or not tool_capable(m): continue
        pr = m.get("pricing") or {}
        pin, pout = perM(pr.get("prompt")), perM(pr.get("completion"))
        free = (pin == 0 and pout == 0)
        rows.append((0 if free else 1, pin if pin is not None else 9e9, mid))
    rows.sort()
    ranked = [r[2] for r in rows[:TOP_N]]
# OpenRouter's own Free Models Router: zero-cost, picks a free model per
# request and filters for tool support itself. Pinned first if available.
FREE_ROUTER = "openrouter/free"
if FREE_ROUTER in catalog and FREE_ROUTER not in ranked:
    ranked.insert(0, FREE_ROUTER)
elif FREE_ROUTER not in catalog:
    print(f"openrouter/{FREE_ROUTER}\t{'FREE':<18} {FREE_ROUTER} (rotating free models)")
for slug in ranked:
    print(f"openrouter/{slug}\t{fmt(catalog[slug])}")
PY
    [[ -s "${OR_ROWS_FILE}" ]] || { echo "❌ No OpenRouter models parsed."; [[ -z "${OU_KEY}" ]] && exit 1; echo "   Continuing with OU Sandbox only."; OR_KEY=""; }
  fi
fi

# ---- load rows ------------------------------------------------------------
REFS=(); LINES=()
if [[ -s "${OU_ROWS_FILE}" ]]; then
  while IFS=$'\t' read -r ref line; do REFS+=("${ref}"); LINES+=("${line}"); done < "${OU_ROWS_FILE}"
fi
N_OU=${#REFS[@]}
if [[ -s "${OR_ROWS_FILE}" ]]; then
  while IFS=$'\t' read -r ref line; do REFS+=("${ref}"); LINES+=("${line}"); done < "${OR_ROWS_FILE}"
fi
N_ALL=${#REFS[@]}
(( N_ALL )) || { echo "❌ No models available from any provider."; exit 1; }

describe() { # describe <ref> -> pretty line for that ref
  local ref="$1" i
  for i in "${!REFS[@]}"; do [[ "${REFS[$i]}" == "${ref}" ]] && { echo "${LINES[$i]}"; return; }; done
  echo "${ref}"
}

# Validate a typed OpenRouter model id against the live catalog.
# Prints "ok <price line>" or "missing" or "notools".
check_or_model() {
  python3 - "$1" <<'PY'
import json, sys
mid = sys.argv[1]
try:
    with open("/tmp/or_models.json") as f:
        catalog = {m.get("id"): m for m in json.load(f).get("data",[])}
except Exception:
    catalog = {}
m = catalog.get(mid)
if not m: print("missing"); sys.exit()
if mid != "openrouter/free" and "tools" not in (m.get("supported_parameters") or []):
    print("notools"); sys.exit()
def perM(v):
    try: return float(v)*1e6
    except Exception: return None
pr = m.get("pricing") or {}
pin, pout = perM(pr.get("prompt")), perM(pr.get("completion"))
if pin == 0 and pout == 0: price = "FREE"
elif pin is not None and pout is not None: price = f"${pin:.2f}/${pout:.2f} /M"
else: price = "price n/a"
ctx = m.get("context_length") or 0
ctxs = f"{ctx//1000}k" if ctx else "?"
print(f"ok {price:<18} {mid} ({ctxs})")
PY
}

show_menu() { # show_menu <role: primary|fallback>
  local role="$1" i
  echo
  if (( N_OU )); then
    echo "OU AI Sandbox models (litellm):"
    for (( i=0; i<N_OU; i++ )); do printf "  %3d) %s\n" "$((i+1))" "${LINES[$i]}"; done
  fi
  if (( N_ALL > N_OU )); then
    echo "OpenRouter — top $((N_ALL-N_OU)) by weekly popularity (tool-capable):"
    for (( i=N_OU; i<N_ALL; i++ )); do printf "  %3d) %s\n" "$((i+1))" "${LINES[$i]}"; done
    echo "    T) type any other OpenRouter model id (validated against the live catalog)"
  fi
  [[ "${role}" == "fallback" ]] && echo "    0) no fallback"
}

pick_model() { # pick_model <role> -> sets PICKED (ref) and PICKED_DESC; empty PICKED = none
  local role="$1" default_hint choice res
  if [[ "${role}" == "primary" ]]; then default_hint="[default 1]"; else default_hint="[default 0 = none]"; fi
  while true; do
    show_menu "${role}"
    echo
    read -rp "Pick the ${role} model ${default_hint}: " choice < "${TTY}" || choice=""
    if [[ -z "${choice}" ]]; then
      if [[ "${role}" == "primary" ]]; then choice=1; else PICKED=""; PICKED_DESC="(none)"; return; fi
    fi
    if [[ "${role}" == "fallback" && "${choice}" == "0" ]]; then PICKED=""; PICKED_DESC="(none)"; return; fi
    if [[ "${choice}" =~ ^[Tt]$ ]]; then
      (( N_ALL > N_OU )) || { echo "Typed entry needs an OpenRouter key."; continue; }
      read -rp "OpenRouter model id (vendor/model, e.g. anthropic/claude-sonnet-5): " mid < "${TTY}" || mid=""
      [[ -z "${mid}" ]] && continue
      res="$(check_or_model "${mid}")"
      case "${res}" in
        missing) echo "❌ '${mid}' is not in OpenRouter's live catalog — check the spelling at openrouter.ai/models."; continue ;;
        notools) echo "❌ '${mid}' exists but does not support tool calling, which OpenClaw requires — pick another."; continue ;;
        ok\ *)   PICKED="openrouter/${mid}"; PICKED_DESC="${res#ok }"; return ;;
        *)       echo "❌ Could not validate '${mid}' — try again."; continue ;;
      esac
    fi
    if [[ "${choice}" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= N_ALL )); then
      PICKED="${REFS[$((choice-1))]}"; PICKED_DESC="${LINES[$((choice-1))]}"; return
    fi
    echo "Please enter a number between 1 and ${N_ALL}$( [[ "${role}" == "fallback" ]] && echo ", 0 for none," ) or T."
  done
}

# ---- choose primary, then fallback (same options both times) ---------------
pick_model primary
PRIMARY="${PICKED}"; PRIMARY_DESC="${PICKED_DESC}"
echo "✓ primary:  ${PRIMARY_DESC}"

pick_model fallback
FALLBACK="${PICKED}"; FALLBACK_DESC="${PICKED_DESC}"
[[ "${FALLBACK}" == "${PRIMARY}" ]] && { echo "(fallback same as primary — skipping fallback)"; FALLBACK=""; FALLBACK_DESC="(none)"; }
echo "✓ fallback: ${FALLBACK_DESC}"

# ---- apply ------------------------------------------------------------------
echo
echo "→ primary: ${PRIMARY}"
if ! openclaw models set "${PRIMARY}"; then
  echo "❌ Could not set primary '${PRIMARY}'."
  echo "   Run 'openclaw models list' for valid refs, and check the gateway is running."
  exit 1
fi
openclaw models fallbacks clear >/dev/null 2>&1 || true
if [[ -n "${FALLBACK}" ]]; then
  echo "→ fallback: ${FALLBACK}"
  openclaw models fallbacks add "${FALLBACK}" || echo "⚠️  Couldn't add fallback '${FALLBACK}' — skipped."
fi

echo
echo "Selected configuration (price per 1M tokens, input/output):"
echo "  primary:  ${PRIMARY_DESC}"
echo "  fallback: ${FALLBACK_DESC}"
echo
echo "Current model configuration:"
openclaw models status 2>/dev/null || echo "⚠️  'openclaw models status' unavailable (is the gateway running?)."
echo "(Hot-reloaded for new sessions. For the chat you're in now, switch with /model.)"
