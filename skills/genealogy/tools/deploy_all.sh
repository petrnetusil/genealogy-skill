#!/bin/bash
# Deploys the main family-tree website and every partial website ("variant") from data/variants.json to Cloudflare,
# then checks that every login gate answers HTTP 401 without the cookie.
#   main site: web/ → npm run deploy-cloudflare (export, build, web/scripts/deploy_cloudflare.mjs);
#              with "cloudflare": {"domain": "…"} in data/website.json the custom domain is attached as well
#   variants:  python3 -I tools/site_variants.py <name> --deploy (builds variants/<name>/ and deploys it the same way)
# Missing or empty data/variants.json = only the main site. Format: see tools/site_variants.py --help.
# Usage (from the project root):  bash tools/deploy_all.sh           – main site and all variants
#                                 bash tools/deploy_all.sh main      – only the main site
#                                 bash tools/deploy_all.sh <name>    – only one variant
#                                 bash tools/deploy_all.sh check     – only the gate check
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -d /opt/local/bin ]] && export PATH=/opt/local/bin:$PATH   # ImageMagick from MacPorts (macOS), if present
if [[ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" && -f web/.nvmrc ]]; then   # Node version of the website (web/.nvmrc)
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"; . "$NVM_DIR/nvm.sh" >/dev/null
  nvm use "$(tr -d '[:space:]' < web/.nvmrc)" >/dev/null || true
fi
WHAT="${1:-all}"

if [[ "$WHAT" != "check" ]]; then
  # list of people for every news version (the newest version gets a snapshot of the data)
  [[ -f tools/news_people.py ]] && python3 -I tools/news_people.py
fi

if [[ "$WHAT" == "all" || "$WHAT" == "main" ]]; then
  echo "== main website"
  python3 -I tools/site_variants.py --deploy-main
fi
VARIANTS=$(python3 -I tools/site_variants.py --list)
if [[ "$WHAT" != "all" && "$WHAT" != "main" && "$WHAT" != "check" ]] && ! grep -qx -- "$WHAT" <<<"$VARIANTS"; then
  echo "ERROR: \"$WHAT\" is neither main, check nor a variant in data/variants.json (${VARIANTS//$'\n'/, })." >&2
  exit 2
fi
for v in $VARIANTS; do
  if [[ "$WHAT" == "all" || "$WHAT" == "$v" ]]; then
    echo "== variant $v"
    python3 -I tools/site_variants.py "$v" --deploy
  fi
done

echo "== gate check (401 expected without the cookie)"
FAILED=0
while IFS=$'\t' read -r site url; do
  [[ -z "$site" ]] && continue
  if [[ -z "$url" ]]; then
    echo "$site: address unknown (not deployed yet?)"; FAILED=1; continue
  fi
  code=$(python3 -I tools/polite.py curl -s -o /dev/null -w "%{http_code}" "$url" || true)
  echo "$site: $code  $url"
  [[ "$code" == "401" ]] || FAILED=1
done < <(python3 -I tools/site_variants.py --urls)
if [[ "$FAILED" != 0 ]]; then
  echo "WARNING: some gate did not answer 401 – the website may be open to anyone. Check it." >&2
  exit 1
fi
